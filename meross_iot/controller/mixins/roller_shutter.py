import logging
from typing import Optional, Dict

from meross_iot.model.enums import Namespace, RollerShutterState

_LOGGER = logging.getLogger(__name__)


class RollerShutterTimerMixin:
    _execute_command: callable
    check_full_update_done: callable
    uuid: str
    _shutter__state_by_channel: Dict[int, RollerShutterState]
    _shutter__position_by_channel: Dict[int, int]
    _shutter__config_by_channel: Dict[int, Dict]

    def __init__(self, device_uuid: str,
                 manager,
                 **kwargs):
        super().__init__(device_uuid=device_uuid, manager=manager, **kwargs)
        self._shutter__state_by_channel = {}
        self._shutter__position_by_channel = {}
        self._shutter__config_by_channel = {}

    async def async_handle_push_notification(self, namespace: Namespace, data: dict) -> bool:
        locally_handled = False

        if namespace == Namespace.ROLLER_SHUTTER_STATE:
            _LOGGER.debug(f"{self.__class__.__name__} handling push notification for namespace "
                          f"{namespace}")
            payload = data.get('state')
            if payload is None:
                _LOGGER.error(f"{self.__class__.__name__} could not find 'state' attribute in push notification data: "
                              f"{data}")
                locally_handled = False
            else:
                # The roller shutter timer state push notification contains an object for every channel handled by the
                # device
                for roller_shutter in payload:
                    channel_index = roller_shutter['channel']
                    state = RollerShutterState(roller_shutter['state']) # open (position=100, state=1), close (position=0, state=2), stop (position=-1, state=0)
                    self._shutter__state_by_channel[channel_index] = state
                    locally_handled = True
        elif namespace == Namespace.ROLLER_SHUTTER_POSITION:
            _LOGGER.debug(f"{self.__class__.__name__} handling push notification for namespace "
                          f"{namespace}")
            payload = data.get('position')
            if payload is None:
                _LOGGER.error(f"{self.__class__.__name__} could not find 'position' attribute in push notification data: "
                              f"{data}")
                locally_handled = False
            else:
                # The roller shutter timer position push notification contains an object for every channel handled by the
                # device
                for roller_shutter in payload:
                    channel_index = roller_shutter['channel']
                    position = roller_shutter['position'] # open (position=100, state=1), close (position=0, state=2), stop (position=-1, state=0)
                    self._shutter__position_by_channel[channel_index] = position
                    locally_handled = True

        # Always call the parent handler when done with local specific logic. This gives the opportunity to all
        # ancestors to catch all events.
        parent_handled = await super().async_handle_push_notification(namespace=namespace, data=data)
        return locally_handled or parent_handled

    async def async_open(self, channel: int = 0, *args, **kwargs) -> None:
        """
        Operates the roller shutter: sends the open command.

        :param channel: channel to operate: defaults to 0

        :return: None
        """
        await self._async_operate(position=100, channel=channel, *args, **kwargs)

    async def async_stop(self, channel: int = 0, *args, **kwargs) -> None:
        """
        Operates the roller shutter: sends the stop command.

        :param channel: channel to operate: defaults to 0

        :return: None
        """
        await self._async_operate(position=-1, channel=channel, *args, **kwargs)

    async def async_close(self, channel: int = 0, *args, **kwargs) -> None:
        """
        Operates the roller shutter: sends the close command.

        :param channel: channel to operate: defaults to 0

        :return: None
        """
        await self._async_operate(position=0, channel=channel, *args, **kwargs)

    async def _async_operate(self, position: int, channel: int = 0, timeout: Optional[float] = None, *args, **kwargs) -> None:
        payload = {'position': {"position": position, "channel": channel}}
        await self._execute_command(method="SET",
                                    namespace=Namespace.ROLLER_SHUTTER_POSITION,
                                    payload=payload,
                                    timeout=timeout)
        # Respect to other devices, we don't assume the command was immediately successful as the
        # state/position change might take some time to take place.
        # self.__state_by_channel[channel] = state
        # self._roller_shutter_position_by_channel[channel] = position

    async def async_set_position(self, position: int, channel: int = 0, timeout: Optional[float] = None, *args, **kwargs) -> None:
        return await self._async_operate(position=position, channel=channel, timeout=timeout, *args, **kwargs)

    async def async_update(self, timeout: Optional[float] = None, *args, **kwargs) -> None:
        # Call the super implementation
        await super().async_update(*args, **kwargs)
        # Update the configuration at the same time
        await self.async_fetch_config()

    async def async_fetch_config(self, timeout: Optional[float] = None, *args, **kwargs) -> None:
        data = await self._execute_command(method="GET",
                                    namespace=Namespace.ROLLER_SHUTTER_CONFIG,
                                    payload={},
                                    timeout=timeout)
        config = data.get('config')
        for d in config:
            channel = d['channel']
            channel_config = d.copy()
            self._shutter__config_by_channel[channel] = channel_config

    def get_open_timer_duration_millis(self, channel: int = 0, *args, **kwargs) -> int:
        self.check_full_update_done()
        return self._shutter__config_by_channel.get(channel).get("signalOpen")

    def get_close_timer_duration_millis(self, channel: int = 0, *args, **kwargs) -> int:
        self.check_full_update_done()
        return self._shutter__config_by_channel.get(channel).get("signalClose")

    async def async_set_config(self, open_timer_seconds: int, close_timer_seconds: int, channel: int = 0, timeout: Optional[float] = None, *args, **kwargs) -> None:
        """
        Sets the configuration parameters for the roller shutter on the given channel.
        :param open_timer_seconds: open timer, min 10, max 120.
        :param close_timer_seconds: close timer, min 10, max 120.
        :param channel: channel to configure
        :param timeout:
        :return:
        """
        if open_timer_seconds < 10 or open_timer_seconds > 120:
            raise ValueError("Invalid open_timer_seconds timer, must be between 10 and 120 seconds.")
        if close_timer_seconds < 10 or close_timer_seconds > 120:
            raise ValueError("Invalid close_timer_seconds timer, must be between 10 and 120 seconds.")

        config = {"channel": channel, "signalOpen": 1000*open_timer_seconds, "signalClose": 1000*close_timer_seconds}
        res = await self._execute_command(method="SET",
                                    namespace=Namespace.ROLLER_SHUTTER_CONFIG,
                                    payload={"config": config},
                                    timeout=timeout)
        self._shutter__config_by_channel[channel] = config

    def get_status(self, channel: int = 0, *args, **kwargs) -> RollerShutterState:
        """
        The current roller shutter status. Returns 1 if the given roller shutter is open, 2 if it is close, 0 if it is stop.

        :param channel: channel of which status is needed

        :return: 1 if the given roller shutter is opened, 2 if it is closed, 0 if it is stopped.
        """
        self.check_full_update_done()
        state = self._shutter__state_by_channel.get(channel)
        return RollerShutterState(state) if state is not None else RollerShutterState.UNKNOWN

    def get_position(self, channel: int = 0, *args, **kwargs) -> Optional[int]:
        """
        The current roller shutter position. Returns 100 if the given roller shutter is open, 0 if it is close, -1 if it is stop.

        :param channel: channel of which status is needed

        :return: 100 if the given roller shutter is opened, 0 if it is closed, -1 if it is stopped.
        """
        self.check_full_update_done()
        return self._shutter__position_by_channel.get(channel)