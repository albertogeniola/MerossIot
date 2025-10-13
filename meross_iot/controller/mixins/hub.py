import logging
from typing import Optional, List, Iterable, Dict

from meross_iot.controller.device import GenericSubDevice, BaseDevice
from meross_iot.model.enums import Namespace

_LOGGER = logging.getLogger(__name__)


# TODO: implement HUB_BATTERY and HUB_ONLINE Mixins


class HubMixin(BaseDevice):
    __PUSH_MAP = {
        Namespace.HUB_MTS100_ALL.value: 'all',

        Namespace.HUB_ONLINE.value: 'online',
        Namespace.HUB_BATTERY.value: 'battery',

        Namespace.HUB_MTS100_TEMPERATURE.value: 'temperature',
        Namespace.HUB_MTS100_MODE.value: 'mode',
        Namespace.HUB_MTS100_ADJUST.value: 'adjust',

        Namespace.HUB_SENSOR_ALL.value: 'all',
        Namespace.HUB_SENSOR_ALERT.value: 'alert',
        Namespace.HUB_SENSOR_TEMPHUM.value: 'tempHum',
        Namespace.HUB_SENSOR_DOORWINDOW.value: 'doorWindow',
        Namespace.HUB_TOGGLEX.value: 'togglex',
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
        data = await self._execute_command(method="GET", namespace=Namespace.SYSTEM_ALL, payload={})
        for sd in data['all']['digest']['hub']['subdevice']:
            sub_device = build_subdevice_from_digest_payload(hub_device=self, digest_payload=sd)
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
            # TODO: make sure we have all subdevices in place and remove the ones
            #  that are no longer in place.

            for subdevice_state in hub_data["subdevice"]:
                subdev_id = subdevice_state["id"]

                device = self.__sub_devices.get(subdev_id)
                if device is None:
                    _LOGGER.error(f"SubDevice {subdev_id} is not registered to hub {self.name} ({self.uuid})."
                                  f"State update for this SubDevice will be ignored.")
                else:
                    # Propagate state update
                    locally_handled = locally_handled or await device.async_notify_hub_update(data=subdevice_state)

        super_handled = await super().async_handle_update(namespace=namespace, data=data)
        return super_handled or locally_handled

    async def _async_handle_push_notification(self, namespace: str, data: dict) -> bool:
        locally_handled = False

        # Always call the parent handler when done with local specific logic. This gives the opportunity to all
        # ancestors to catch all events.
        parent_handled = await super()._async_handle_push_notification(namespace=namespace, data=data)

        # We will take into account all events that are explicitly handled by this mixin or if the associated
        # namespace starts with the "Appliance.Hub." prefix. In case we don't explicitly handle that
        # we'll try to parse the payload key-accessor by looking at the last token.
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
                _LOGGER.info(f"The namespace {namespace} is not explicitly handled by "
                             f"this mixin ({self.__class__}), however we guessed an accessor that seems compatible "
                             f"with the namespace ({normalized_accessor}). We'll attempt to use that.")
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
                        return False
                    else:
                        await subdev.async_dispatch_push_notification(namespace=namespace, data=subdev_state)
                    locally_handled = True

        return locally_handled or parent_handled
