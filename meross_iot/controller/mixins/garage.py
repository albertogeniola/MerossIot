import logging
from typing import Optional

from meross_iot.model.enums import Namespace

_LOGGER = logging.getLogger(__name__)


class GarageOpenerMixin:
    _execute_command: callable
    check_full_update_done: callable
    uuid: str

    def __init__(self, device_uuid: str,
                 manager,
                 **kwargs):
        super().__init__(device_uuid=device_uuid, manager=manager, **kwargs)
        self._door_open_state_by_channel = {}

    async def async_handle_push_notification(self, namespace: Namespace, data: dict) -> bool:
        locally_handled = False

        if namespace == Namespace.GARAGE_DOOR_STATE:
            _LOGGER.debug(f"{self.__class__.__name__} handling push notification for namespace "
                          f"{namespace}")
            payload = data.get('state')
            if payload is None:
                _LOGGER.error(f"{self.__class__.__name__} could not find 'state' attribute in push notification data: "
                              f"{data}")
                locally_handled = False
            else:
                # The door opener state push notification contains an object for every channel handled by the
                # device
                for door in payload:
                    channel_index = door['channel']
                    state = door['open'] == 1
                    self._door_open_state_by_channel[channel_index] = state
                    locally_handled = True

        # Always call the parent handler when done with local specific logic. This gives the opportunity to all
        # ancestors to catch all events.
        parent_handled = await super().async_handle_push_notification(namespace=namespace, data=data)
        return locally_handled or parent_handled

    async def async_handle_update(self, namespace: Namespace, data: dict) -> bool:
        _LOGGER.debug(f"Handling {self.__class__.__name__} mixin data update.")
        locally_handled = False
        if namespace == Namespace.SYSTEM_ALL:
            doors_data = data.get('all', {}).get('digest', {}).get('garageDoor', [])
            for door in doors_data:
                channel_index = door['channel']
                state = door['open'] == 1
                self._door_open_state_by_channel[channel_index] = state
            locally_handled = True

        super_handled = await super().async_handle_update(namespace=namespace, data=data)
        return super_handled or locally_handled

    async def async_open(self, channel: int = 0, *args, **kwargs) -> None:
        """
        Operates the door: sends the open command.

        :param channel: channel to operate: defaults to 0

        :return: None
        """
        await self._async_operate(state=True, channel=channel, *args, **kwargs)

    async def async_close(self, channel: int = 0, *args, **kwargs) -> None:
        """
        Operates the door: sends the close command.

        :param channel: channel to operate: defaults to 0

        :return: None
        """
        await self._async_operate(state=False, channel=channel, *args, **kwargs)

    async def _async_operate(self, state: bool, channel: int = 0, skip_rate_limits: bool = False, drop_on_overquota: bool = True, *args, **kwargs) -> None:
        payload = {"state": {"channel": channel, "open": 1 if state else 0, "uuid": self.uuid}}
        await self._execute_command(method="SET",
                                    namespace=Namespace.GARAGE_DOOR_STATE,
                                    payload=payload,
                                    skip_rate_limits=skip_rate_limits,
                                    drop_on_overquota=drop_on_overquota)

    def get_is_open(self, channel: int = 0, *args, **kwargs) -> Optional[bool]:
        """
        The current door-open status. Returns True if the given door is open, False otherwise.

        :param channel: channel of which status is needed

        :return: False if the door is closed, True otherwise
        """
        self.check_full_update_done()
        return self._door_open_state_by_channel.get(channel)
