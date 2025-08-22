import logging
from typing import Optional

from meross_iot.controller.mixins.utilities import DynamicFilteringMixin
from meross_iot.model.enums import Namespace

_LOGGER = logging.getLogger(__name__)


class HubMixn(DynamicFilteringMixin):
    __PUSH_MAP = {
        Namespace.HUB_ONLINE: 'online',
        Namespace.HUB_TOGGLEX: 'togglex',
        Namespace.HUB_BATTERY: 'battery'
    }

    @staticmethod
    def filter(device_ability : str, device_name : str,**kwargs):
        return device_ability == Namespace.HUB_ONLINE.value or device_ability == Namespace.HUB_TOGGLEX.value
    
    def __init__(self, device_uuid: str,
                 manager,
                 **kwargs):
        super().__init__(device_uuid=device_uuid, manager=manager, **kwargs)

    async def async_handle_push_notification(self, namespace: Namespace, data: dict) -> bool:
        locally_handled = False
        target_data_key = self.__PUSH_MAP.get(namespace)

        if target_data_key is not None:
            _LOGGER.debug(f"{self.__class__.__name__} handling push notification for namespace {namespace}")
            payload = data.get(target_data_key)
            if payload is None:
                _LOGGER.error(f"{self.__class__.__name__} could not find {target_data_key} attribute in push notification data: "
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
                        await subdev.async_handle_subdevice_notification(namespace=namespace, data=subdev_state)
                locally_handled = True


        return locally_handled


class HubMs100Mixin(DynamicFilteringMixin):
    __PUSH_MAP = {
        # TODO: check this
        Namespace.HUB_SENSOR_ALERT: 'alert',
        Namespace.HUB_SENSOR_TEMPHUM: 'tempHum',
        Namespace.HUB_SENSOR_ALL: 'all'
    }
    _execute_command: callable
    get_subdevice: callable
    uuid: str

    def __init__(self, device_uuid: str,
                 manager,
                 **kwargs):
        super().__init__(device_uuid=device_uuid, manager=manager, **kwargs)
    
    @staticmethod
    def filter(device_ability : str, device_name : str,**kwargs):
        return device_ability == Namespace.HUB_SENSOR_ALL.value or device_ability == Namespace.HUB_SENSOR_ALERT.value or device_ability == Namespace.HUB_SENSOR_TEMPHUM.value
    
    async def _async_request_update(self, timeout: Optional[float] = None, *args, **kwargs) -> None:
        result = await self._execute_command(method="GET",
                                             namespace=Namespace.HUB_SENSOR_ALL,
                                             payload={'all': []},
                                             timeout=timeout)
        subdevs_data = result.get('all', [])
        for d in subdevs_data:
            dev_id = d.get('id')
            target_device = self.get_subdevice(subdevice_id=dev_id)
            if target_device is None:
                _LOGGER.warning(f"Received data for subdevice {target_device}, which has not been registered with this"
                                f"hub yet. This update will be ignored.")
            else:
                await target_device.async_handle_subdevice_notification(namespace=Namespace.HUB_SENSOR_ALL, data=d)

    async def async_handle_push_notification(self, namespace: Namespace, data: dict) -> bool:
        locally_handled = False
        target_data_key = self.__PUSH_MAP.get(namespace)

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
                        await subdev.async_handle_subdevice_notification(namespace=namespace, data=subdev_state)
                locally_handled = True


        return locally_handled


class HubMts100Mixin(DynamicFilteringMixin):
    __PUSH_MAP = {
        Namespace.HUB_MTS100_ALL: 'all',
        Namespace.HUB_MTS100_MODE: 'mode',
        Namespace.HUB_MTS100_TEMPERATURE: 'temperature'
    }
    _execute_command: callable
    get_subdevice: callable
    uuid: str

    def __init__(self, device_uuid: str,
                 manager,
                 **kwargs):
        super().__init__(device_uuid=device_uuid, manager=manager, **kwargs)
    
    @staticmethod
    def filter(device_ability : str, device_name : str,**kwargs):
        return device_ability == Namespace.HUB_MTS100_ALL.value or device_ability == Namespace.HUB_MTS100_MODE.value or device_ability == Namespace.HUB_MTS100_TEMPERATURE.value
    
    async def _async_request_update(self, timeout: Optional[float] = None, *args, **kwargs) -> None:
        try:
            result = await self._execute_command(method="GET",
                                                 namespace=Namespace.HUB_MTS100_ALL,
                                                 payload={'all': []},
                                                 timeout=timeout)
            subdevs_data = result.get('all', [])
            for d in subdevs_data:
                dev_id = d.get('id')
                target_device = self.get_subdevice(subdevice_id=dev_id)
                if target_device is None:
                    _LOGGER.warning(f"Received data for subdevice {target_device}, which has not been registered with this"
                                    f"hub yet. This update will be ignored.")
                else:
                    await target_device.async_handle_subdevice_notification(namespace=Namespace.HUB_MTS100_ALL, data=d)
        except Exception as e:
            _LOGGER.exception("Error occurred during subdevice update")

    async def async_handle_push_notification(self, namespace: Namespace, data: dict) -> bool:
        locally_handled = False
        target_data_key = self.__PUSH_MAP.get(namespace)

        if target_data_key is not None:
            _LOGGER.debug(f"{self.__class__.__name__} handling push notification for namespace {namespace}")
            payload = data.get(target_data_key)
            if payload is None:
                _LOGGER.error(f"{self.__class__.__name__} could not find {target_data_key} attribute in push notification data: "
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
                        locally_handled = await subdev.async_handle_subdevice_notification(namespace=namespace, data=subdev_state)
                        if locally_handled:
                            break


        return locally_handled
