import logging
from typing import Optional, List, Iterable, Dict

from meross_iot.controller.device import GenericSubDevice, BaseDevice
from meross_iot.model.enums import Namespace, OnlineStatus

_LOGGER = logging.getLogger(__name__)


class HubMixin(BaseDevice):
    __PUSH_MAP = {
        Namespace.HUB_MTS100_ALL: 'all',

        Namespace.HUB_UNBIND: 'unbind',
        Namespace.HUB_ONLINE: 'online',
        Namespace.HUB_BATTERY: 'battery',

        Namespace.HUB_MTS100_TEMPERATURE: 'temperature',
        Namespace.HUB_MTS100_MODE: 'mode',
        Namespace.HUB_MTS100_ADJUST: 'adjust',

        Namespace.HUB_SENSOR_ALL: 'all',
        Namespace.HUB_SENSOR_ALERT: 'alert',
        Namespace.HUB_SENSOR_TEMPHUM: 'tempHum',
        Namespace.HUB_SENSOR_DOORWINDOW: 'doorWindow',
        Namespace.HUB_SENSOR_WATERLEAK: 'waterLeak',

        Namespace.HUB_TOGGLEX: 'togglex',
    }

    def __init__(self, device_uuid: str,
                 manager,
                 **kwargs):
        super().__init__(device_uuid=device_uuid, manager=manager, **kwargs)
        self.__sub_devices: Dict[str, GenericSubDevice] = {}

    def get_subdevices(self) -> Iterable[GenericSubDevice]:
        return self.__sub_devices.values()

    def get_subdevice(self, subdevice_id: str) -> Optional[GenericSubDevice]:
        return self.__sub_devices.get(subdevice_id)

    async def async_discover_subdevices(self) -> List[GenericSubDevice]:
        from meross_iot.device_factory import build_subdevice_from_digest_payload
        res = []
        data_digest = await self._execute_command(method="GET", namespace=Namespace.SYSTEM_ALL, payload={})
        data_version = await self._execute_command(method="GET", namespace=Namespace.HUB_SUBDEVICE_VERSION, payload={'version':[]})

        for sd in data_digest['all']['digest']['hub']['subdevice']:
            subdevice_version = next(filter(lambda x: x, data_version['version']))
            sub_device = build_subdevice_from_digest_payload(hub_device=self, digest_payload=sd, version_payload=subdevice_version)
            if sub_device.subdevice_id not in self.__sub_devices:
                self.__sub_devices[sub_device.subdevice_id] = sub_device
                res.append(sub_device)
        return res

    # We do not override the async_update here: we rely on the base implementation
    #  specifically the SYSTEM_ALL mixin will also take care of handling subdevice
    #  updates

    async def async_handle_update(self, namespace: Namespace, data: dict) -> bool:
        # The hub is in charge of handling the update also for its managed subdevices
        # Here we should add/remove subdevices and propagate their state update.
        locally_handled = False
        if namespace == Namespace.SYSTEM_ALL:
            hub_data = data["all"]["digest"]["hub"]

            # A full update can reveal sub-device pairing changes: e.g. a subdevice has been removed or added
            # to the hub. In case we see inconsistency, we show that here.
            # For now, just log this edge case.
            state_update_ids = set([x['id'] for x in hub_data["subdevice"]])
            known_ids = set(self.__sub_devices.keys())
            removed_ids = known_ids - state_update_ids
            for removed_id in removed_ids:
                sd = self.__sub_devices[removed_id]
                if sd.online_status != OnlineStatus.UNKNOWN:
                    _LOGGER.warning(f"Subdevice {removed_id} no longer present into Hub {self.name} ({self.uuid})."
                                    f"Setting their state to UNKNOWN.")
                    # We are simulating an update from the broker to put the device into an unknown state.
                    await sd.async_notify_hub_update(data={'status': OnlineStatus.UNKNOWN.value})

            added_ids = state_update_ids - known_ids
            if added_ids:
                _LOGGER.info(f"New subdevices {added_ids} detected for Hub {self.name} ({self.uuid}) during"
                             f"state update. Please run the manager's discovery to handle them. ")

            for subdevice_state in hub_data["subdevice"]:
                subdev_id = subdevice_state["id"]

                device = self.__sub_devices.get(subdev_id)
                if device is None:
                    _LOGGER.error(f"SubDevice {subdev_id} is not registered to hub {self.name} ({self.uuid})."
                                  f"State update for this SubDevice will be ignored.")
                else:
                    # Propagate state update
                    handled = await device.async_notify_hub_update(data=subdevice_state)
                    locally_handled = locally_handled or handled

        super_handled = await super().async_handle_update(namespace=namespace, data=data)
        return super_handled or locally_handled

    async def _async_handle_push_notification(self, namespace: Namespace, data: dict) -> bool:
        locally_handled = False
        subdevice_to_release: GenericSubDevice|None = None

        # Always call the parent handler when done with local specific logic. This gives the opportunity to all
        # ancestors to catch all events.
        parent_handled = await super()._async_handle_push_notification(namespace=namespace, data=data)

        # Let's first handle push notifications at hub level.
        # Fist handle subdevice-bind and subdevice-unbind.
        # For now, we just log a message.
        if namespace == Namespace.HUB_BIND:
            bind_data = data['bind'][0]
            _LOGGER.info(f"A new subdevice has been bound to this hub. Subdevice id {bind_data['id']} - type {bind_data['deviceType']}.")
            return True  # We assume we handled the push notification

        elif namespace == Namespace.HUB_UNBIND:
            # When handling unbinding notifications, we need to first push the notification to the subdevices
            # and only then we can unload the underlying objects. This is necessary in order to allow subdevice
            # event handlers to run correctly.
            unbind_data = data['unbind'][0]
            subdevice_to_release = self.get_subdevice(subdevice_id=unbind_data['id'])
            if subdevice_to_release is not None:
                _LOGGER.warning(f"Subdevice has been unbound from this hub. Subdevice id {unbind_data['id']}.")
                # We do nothing more now: the SubDevice base implementation will update the "onlinestatus" to
                # UNKNOWN to reflect the device unavailability.
            else:
                _LOGGER.error(f"Received an unbind event for a subdevice ({unbind_data['id']}) that does not belong to this HUB ({self.name} - {self.uuid}).")

        # Hubs receive push notifications for their sub-devices.
        # This method routes the push notification to the corresponding subdevice.
        # We assume that all push notifications with a namespace starting with "Appliance.Hub.*"
        # and containing an "id" attribute should be routed to sub-devices.
        # The data format is typically {'accessor': [{'id':'', ...}]}.
        # The accessor key can be derived from the last part of the namespace (e.g., "Appliance.Hub.WaterLeak" -> "waterLeak").
        # We use a combination of static map strings and dynamic accessor guessing via the namespace.
        target_data_key = self.__PUSH_MAP.get(namespace)

        if target_data_key is None and namespace.startswith("Appliance.Hub."):
            _LOGGER.debug(
                f"The namespace {namespace} is not explicitly handled by "
                f"this mixin ({self.__class__}). We'll try guessing the accessor.")
            accessor = namespace.split(".")[-1]
            normalized_accessor = accessor[0].lower() + accessor[1:]

            # Some accessors need to be lower-cased (e.g. togglex).
            if normalized_accessor not in data:
                lowercased = normalized_accessor.lower()
                if lowercased in data:
                    normalized_accessor = lowercased

            # We will only proceed with this accessor if it's actually available into the data payload
            if normalized_accessor in data:
                _LOGGER.debug(f"Guessing accessor ({normalized_accessor}) for namespace ({normalized_accessor}).")
                target_data_key = normalized_accessor

        if target_data_key is not None:
            _LOGGER.debug(f"{self.__class__.__name__} handling push notification for namespace {namespace}")
            payload = data.get(target_data_key)
            if payload is None:
                _LOGGER.error(
                    f"{self.__class__.__name__} could not find {target_data_key} attribute in push notification data: "
                    f"{data}")
                locally_handled = False
            else:
                notification_data = data.get(target_data_key, [])
                for subdev_state in notification_data:
                    subdev_id = subdev_state.get('id')

                    # Check the specific subdevice has been registered with this hub...
                    subdev = self.get_subdevice(subdevice_id=subdev_id)
                    if subdev is None:
                        _LOGGER.warning(
                            f"Received an update for a subdevice (id {subdev_id}) that has not yet been "
                            f"registered with this hub. The update will be skipped.")
                        continue
                    else:
                        locally_handled = await subdev.async_dispatch_push_notification(namespace=namespace, data=subdev_state)

        if subdevice_to_release is not None:
            subdevice_to_release.dismiss()
            del self.__sub_devices[subdevice_to_release.subdevice_id]

        return locally_handled or parent_handled
