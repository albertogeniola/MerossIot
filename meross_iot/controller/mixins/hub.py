import logging

from meross_iot.model.enums import Namespace
from meross_iot.model.push.generic import GenericPushNotification

_LOGGER = logging.getLogger(__name__)


class HubOnlineMixin(object):
    _execute_command: callable

    def __init__(self, device_uuid: str,
                 manager,
                 **kwargs):
        super().__init__(device_uuid=device_uuid, manager=manager, **kwargs)
        self._online_last_active_time = None

    def handle_push_notification(self, push_notification: GenericPushNotification) -> bool:
        locally_handled = False

        if push_notification.namespace == Namespace.HUB_ONLINE:
            _LOGGER.debug(f"{self.__class__.__name__} handling push notification for namespace {push_notification.namespace}")
            payload = push_notification.raw_data.get('online')
            if payload is None:
                _LOGGER.error(f"{self.__class__.__name__} could not find 'online' attribute in push notification data: "
                              f"{push_notification.raw_data}")
                locally_handled = False
            else:
                # TODO: set subdevice status to online
                raise NotImplementedError("TODO")
                locally_handled = True

        # Always call the parent handler when done with local specific logic. This gives the opportunity to all
        # ancestors to catch all events.
        parent_handled = super().handle_push_notification(push_notification=push_notification)
        return locally_handled or parent_handled


class Mts100AllMixin:
    _execute_command: callable
    _abilities_spec: dict
    uuid: str

    def __init__(self, device_uuid: str,
                 manager,
                 **kwargs):
        super().__init__(device_uuid=device_uuid, manager=manager, **kwargs)

    async def async_update(self) -> None:
        # When dealing with hubs, we need to "intercept" the UPDATE()
        await super().async_update()

        # When issuing an update-all command to the hub,
        # we need to query all sub-devices.
        result = await self._execute_command(method="GET",
                                             namespace=Namespace.HUB_MTS100_ALL,
                                             payload={'all': []})
        subdevices_states = result.get('all')
        for subdev_state in subdevices_states:
            subdev_id = subdev_state.get('id')
            self.handle_subdevice_update(subdevice_id=subdev_id, data=subdev_state)

    def handle_subdevice_update(self, subdevice_id: str, data: dict, *args, **kwargs) -> None:
        # Check the specific subdevice has been registered with this hub...
        subdev = self.get_subdevice(subdevice_id=subdevice_id)
        if subdev is None:
            _LOGGER.warning(f"Received an update for a subdevice (id {subdevice_id}) that has not yet been "
                            f"registered with this hub. The update will be skipped.")
            return

        subdev.update_state(**data)
