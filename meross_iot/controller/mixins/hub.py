import logging
from typing import Optional, Awaitable

from meross_iot.model.enums import Namespace
from meross_iot.model.push.generic import GenericPushNotification

_LOGGER = logging.getLogger(__name__)


class Mts100AllMixin:
    _execute_command: callable
    _abilities_spec: dict
    uuid: str

    def __init__(self, device_uuid: str,
                 manager,
                 **kwargs):
        super().__init__(device_uuid=device_uuid, manager=manager, **kwargs)
        # TODO

    def handle_push_notification(self, push_notification: GenericPushNotification) -> bool:
        locally_handled = False
        # TODO
        """
        if push_notification.namespace == Namespace.GARAGE_DOOR_STATE:
            _LOGGER.debug(f"{self.__class__.__name__} handling push notification for namespace "
                          f"{push_notification.namespace}")
            payload = push_notification.raw_data.get('state')
            if payload is None:
                _LOGGER.error(f"{self.__class__.__name__} could not find 'state' attribute in push notification data: "
                              f"{push_notification.raw_data}")
                locally_handled = False
            else:
                # The door opener state push notification contains an object for every channel handled by the
                # device
                for door in payload:
                    channel_index = door['channel']
                    state = door['open'] == 1
                    self._door_open_state_by_channel[channel_index] = state
                    locally_handled = True
        """
        # Always call the parent handler when done with local specific logic. This gives the opportunity to all
        # ancestors to catch all events.
        parent_handled = super().handle_push_notification(push_notification=push_notification)
        return locally_handled or parent_handled

    def handle_update(self, data: dict) -> None:
        # This method will handle the hub-specific events.
        _LOGGER.debug(f"Handling {self.__class__.__name__} mixin data update.")
        hub_data = data.get('all', {}).get('digest', {}).get('hub', [])

        # It seems we don't need to handle anything here, as updates are handled with specific
        # mixins with ALL namespaces.
        # TODO: handle hubid/hubmode?
        # TODO: handle subdevice all events?
        """
        subdevices = hub_data.get('subdevice')
        for subdev in subdevices:
            self.handle_subdevice_update(data=subdev)
        """

        super().handle_update(data=data)

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
