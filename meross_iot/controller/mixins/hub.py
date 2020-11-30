import logging

from meross_iot.model.enums import Namespace

_LOGGER = logging.getLogger(__name__)


class HubMixn(object):
    __PUSH_MAP = {
        Namespace.HUB_ONLINE: 'online',
        Namespace.HUB_TOGGLEX: 'togglex',
        Namespace.HUB_BATTERY: 'battery'
    }

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
                        await subdev.async_handle_push_notification(namespace=namespace, data=subdev_state)
                locally_handled = True

        # Always call the parent handler when done with local specific logic. This gives the opportunity to all
        # ancestors to catch all events.
        parent_handled = await super().async_handle_push_notification(namespace=namespace, data=data)
        return locally_handled or parent_handled


class HubMs100Mixin(object):
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

    async def async_update(self, skip_rate_limits: bool = False, drop_on_overquota: bool = True, *args, **kwargs) -> None:
        # Call the super implementation
        await super().async_update(skip_rate_limits=skip_rate_limits, drop_on_overquota=drop_on_overquota, *args, **kwargs)

        result = await self._execute_command(method="GET",
                                             namespace=Namespace.HUB_SENSOR_ALL,
                                             payload={'all': []},
                                             skip_rate_limits=skip_rate_limits,
                                             drop_on_overquota=drop_on_overquota)
        subdevs_data = result.get('all', [])
        for d in subdevs_data:
            dev_id = d.get('id')
            target_device = self.get_subdevice(subdevice_id=dev_id)
            if target_device is None:
                _LOGGER.warning(f"Received data for subdevice {target_device}, which has not been registered with this"
                                f"hub yet. This update will be ignored.")
            else:
                await target_device.async_handle_push_notification(namespace=Namespace.HUB_SENSOR_ALL, data=d)

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
                        await subdev.async_handle_push_notification(namespace=namespace, data=subdev_state)
                locally_handled = True

        # Always call the parent handler when done with local specific logic. This gives the opportunity to all
        # ancestors to catch all events.
        parent_handled = await super().async_handle_push_notification(namespace=namespace, data=data)
        return locally_handled or parent_handled


class HubMts100Mixin(object):
    __PUSH_MAP = {
        Namespace.HUB_MTS100_ALL: 'all',
        Namespace.HUB_MTS100_MODE: 'mode',
        Namespace.HUB_MTS100_TEMPERATURE: 'temperature'
    }
    _execute_command: callable
    get_subdevices: callable
    uuid: str

    def __init__(self, device_uuid: str,
                 manager,
                 **kwargs):
        super().__init__(device_uuid=device_uuid, manager=manager, **kwargs)

    async def async_update(self, skip_rate_limits: bool = False, drop_on_overquota: bool = True, *args, **kwargs) -> None:
        # Call the super implementation
        await super().async_update(skip_rate_limits=skip_rate_limits, drop_on_overquota=drop_on_overquota, *args, **kwargs)

        result = await self._execute_command(method="GET",
                                             namespace=Namespace.HUB_MTS100_ALL,
                                             payload={'all': []},
                                             skip_rate_limits=skip_rate_limits,
                                             drop_on_overquota=drop_on_overquota)
        subdevs_data = result.get('all', [])
        for d in subdevs_data:
            dev_id = d.get('id')
            target_device = self.get_subdevice(subdevice_id=dev_id)
            if target_device is None:
                _LOGGER.warning(f"Received data for subdevice {target_device}, which has not been registered with this"
                                f"hub yet. This update will be ignored.")
            await target_device.async_handle_push_notification(namespace=Namespace.HUB_MTS100_ALL, data=d)

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
                        await subdev.async_handle_push_notification(namespace=namespace, data=subdev_state)
                locally_handled = True

        # Always call the parent handler when done with local specific logic. This gives the opportunity to all
        # ancestors to catch all events.
        parent_handled = await super().async_handle_push_notification(namespace=namespace, data=data)
        return locally_handled or parent_handled
