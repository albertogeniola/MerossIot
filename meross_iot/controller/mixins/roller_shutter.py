import logging
from typing import Optional

from meross_iot.model.enums import Namespace

_LOGGER = logging.getLogger(__name__)


class RollerShutterTimerMixin:
    _execute_command: callable
    check_full_update_done: callable
    uuid: str

    def __init__(self, device_uuid: str,
                 manager,
                 **kwargs):
        super().__init__(device_uuid=device_uuid, manager=manager, **kwargs)
        self._roller_shutter_state_by_channel = {}
        self._roller_shutter_position_by_channel = {}

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
                    state = roller_shutter['state'] # open (position=100, state=1), close (position=0, state=2), stop (position=-1, state=0)
                    self._roller_shutter_state_by_channel[channel_index] = state
                    locally_handled = True
                    print(f"Push Notification - State: {state}")
                    
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
                    self._roller_shutter_position_by_channel[channel_index] = position
                    locally_handled = True
                    print(f"Push Notification - Position: {position}")

        # Always call the parent handler when done with local specific logic. This gives the opportunity to all
        # ancestors to catch all events.
        parent_handled = await super().async_handle_push_notification(namespace=namespace, data=data)
        return locally_handled or parent_handled

    async def async_handle_update(self, namespace: Namespace, data: dict) -> bool:
        # TODO: The device not send the status or position values, only sends as digest:
        # 'digest': {'triggerx': [], 'timerx': []}}
        _LOGGER.debug(f"Handling {self.__class__.__name__} mixin data update.")
        locally_handled = False
        '''if namespace == Namespace.SYSTEM_ALL:
            roller_shutter_data = data.get('all', {}).get('digest', {})#.get('rollerShutter', [])
            for roller_shutter in roller_shutter_data:
                channel_index = roller_shutter['channel']
                state = roller_shutter['state']
                self._roller_shutter_state_by_channel[channel_index] = state
            locally_handled = True'''   

        super_handled = await super().async_handle_update(namespace=namespace, data=data)
        return super_handled or locally_handled

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

    async def _async_operate(self, position: int, channel: int = 0, skip_rate_limits: bool = False, drop_on_overquota: bool = True, *args, **kwargs) -> None:
        payload = {'position': {"position": position, "channel": channel}}
        await self._execute_command(method="SET",
                                    namespace=Namespace.ROLLER_SHUTTER_POSITION,
                                    payload=payload,
                                    skip_rate_limits=skip_rate_limits,
                                    drop_on_overquota=drop_on_overquota)
        # Respect to other devices, we don't assume the command was immediately successful as the
        # state/position change might take some time to take place.
        # self._roller_shutter_state_by_channel[channel] = state
        # self._roller_shutter_position_by_channel[channel] = position

    def get_status(self, channel: int = 0, *args, **kwargs) -> Optional[int]:
        """
        The current roller shutter status. Returns 1 if the given roller shutter is open, 2 if it is close, 0 if it is stop.

        :param channel: channel of which status is needed

        :return: 1 if the given roller shutter is opened, 2 if it is closed, 0 if it is stopped.
        """
        self.check_full_update_done()
        return self._roller_shutter_state_by_channel.get(channel)

    def get_position(self, channel: int = 0, *args, **kwargs) -> Optional[int]:
        """
        The current roller shutter position. Returns 100 if the given roller shutter is open, 0 if it is close, -1 if it is stop.

        :param channel: channel of which status is needed

        :return: 100 if the given roller shutter is opened, 0 if it is closed, -1 if it is stopped.
        """
        self.check_full_update_done()
        return self._roller_shutter_position_by_channel.get(channel)