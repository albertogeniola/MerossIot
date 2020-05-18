import logging

from meross_iot.controller.subdevice import Mts100v3Valve
from meross_iot.model.enums import Namespace
from meross_iot.model.push.generic import GenericPushNotification

_LOGGER = logging.getLogger(__name__)


class HubOnlineMixin(object):
    _execute_command: callable

    def __init__(self, device_uuid: str,
                 manager,
                 **kwargs):
        super().__init__(device_uuid=device_uuid, manager=manager, **kwargs)

    def handle_push_notification(self, namespace: Namespace, data: dict) -> bool:
        locally_handled = False

        if namespace == Namespace.HUB_ONLINE:
            _LOGGER.debug(f"{self.__class__.__name__} handling push notification for namespace {namespace}")
            payload = data.get('online')
            if payload is None:
                _LOGGER.error(f"{self.__class__.__name__} could not find 'online' attribute in push notification data: "
                              f"{data}")
                locally_handled = False
            else:
                # TODO: set subdevice status to online
                online_data = data.get('online', [])
                for subdev_state in online_data:
                    subdev_id = subdev_state.get('id')

                    # Check the specific subdevice has been registered with this hub...
                    subdev = self.get_subdevice(subdevice_id=subdev_id)
                    if subdev is None:
                        _LOGGER.warning(
                            f"Received an update for a subdevice (id {subdev_id}) that has not yet been "
                            f"registered with this hub. The update will be skipped.")
                        return
                    else:
                        subdev.handle_push_notification(namespace=namespace, data=data)

        # Always call the parent handler when done with local specific logic. This gives the opportunity to all
        # ancestors to catch all events.
        parent_handled = super().handle_push_notification(namespace=namespace, data=data)
        return locally_handled or parent_handled


class Mts100AllMixin:
    _execute_command: callable
    _abilities_spec: dict
    get_subdevice: callable
    uuid: str

    def __init__(self, device_uuid: str,
                 manager,
                 **kwargs):
        super().__init__(device_uuid=device_uuid, manager=manager, **kwargs)

    async def async_update(self, subdevice_ids=(), *args, **kwargs) -> None:
        # When dealing with hubs, we need to "intercept" the UPDATE()
        await super().async_update(*args, **kwargs)

        # When issuing an update-all command to the hub,
        # we need to query all sub-devices.
        result = await self._execute_command(method="GET",
                                             namespace=Namespace.HUB_MTS100_ALL,
                                             payload={'all': [{'id': x} for x in subdevice_ids]})
        subdevices_states = result.get('all')
        for subdev_state in subdevices_states:
            subdev_id = subdev_state.get('id')

            # Check the specific subdevice has been registered with this hub...
            subdev = self.get_subdevice(subdevice_id=subdev_id)
            if subdev is None:
                _LOGGER.warning(f"Received an update for a subdevice (id {subdev_id}) that has not yet been "
                                f"registered with this hub. The update will be skipped.")
                return
            else:
                handled = subdev.handle_push_notification(namespace=Namespace.HUB_MTS100_ALL, data=subdev_state)
                if not handled:
                    _LOGGER.warning(f"Namespace {Namespace.HUB_MTS100_ALL} event was unhandled by subdevice "
                                    f"{subdev.name}")
