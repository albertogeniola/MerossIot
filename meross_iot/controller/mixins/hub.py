import logging
from typing import Optional

from meross_iot.model.enums import Namespace

_LOGGER = logging.getLogger(__name__)


# TODO: implement HUB_BATTERY and HUB_ONLINE Mixins


class HubMixin:
    __PUSH_MAP = {
        Namespace.HUB_MTS100_ALL.value: 'all',

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

    async def async_update(self, timeout: Optional[float] = None, *args, **kwargs) -> None:
        # Call the super implementation
        await super().async_update(*args, **kwargs)

        # When invoking an async update on a HubDevice, just use the HUB_SENSOR_ALL command, as it gets all the data
        # we need with a single update, if available. For now, we don't support sensors not implementing that
        # ability.
        if Namespace.HUB_SENSOR_ALL in self._abilities:
            result = await self._execute_command(method="GET",
                                                 namespace=Namespace.HUB_SENSOR_ALL,
                                                 payload={'all': []},
                                                 timeout=timeout)
            # TODO: handle sensor all update.
            subdevs_data = result.get('all', [])
            for d in subdevs_data:
                dev_id = d.get('id')
                target_device = self.get_subdevice(subdevice_id=dev_id)
                if target_device is None:
                    _LOGGER.warning(
                        f"Received data for subdevice {target_device}, which has not been registered with this"
                        f"hub yet. This update will be ignored.")
                else:
                    await target_device.notify_hub_update(data=d)

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
                        await subdev.dispatch_push_notification(namespace=namespace, data=subdev_state)
                    locally_handled = True

        return locally_handled or parent_handled
