import logging
from typing import Optional, List, Dict

from meross_iot.controller.device import BaseDevice, ChannelInfo, ensure_full_update
from meross_iot.model.enums import Namespace

_LOGGER = logging.getLogger(__name__)


class GarageOpenerMixin(BaseDevice):
    """
    Handles the capabilities offered by `Namespace.GARAGE_DOOR_STATE` and `Namespace.GARAGE_DOOR_MULTIPLECONFIG` namespaces.
    """

    def __init__(self, device_uuid: str,
                 manager,
                 **kwargs):
        super().__init__(device_uuid=device_uuid, manager=manager, **kwargs)
        self.__garage_opener_open_state_by_channel: Dict[int, Optional[bool]] = {}
        self.__garage_opener_config_state_by_channel: Dict[int, Optional[Dict]] = {}

        # Initialize the state attributes
        for c in self._channels:
            self.__garage_opener_open_state_by_channel[c.index] = None
            self.__garage_opener_config_state_by_channel[c.index] = None

    async def async_update(self, *args, **kwargs) -> None:
        """
        Forces a full data update on the device, including the door state and config.
        """
        await super().async_update(*args, **kwargs)
        # We need to fetch the configurations separately since they are not broadcast via SystemAll
        await self.async_garage_opener_fetch_config()

    async def _async_handle_push_notification(self, namespace: Namespace, data: dict) -> bool:
        """
        Handles push notification updates for the garage opener.
        :param namespace: Push notification header namespace
        :param data: Push notification data
        :return: True if the mixin handled the notification, False otherwise
        """
        locally_handled = False

        if namespace == Namespace.GARAGE_DOOR_STATE:
            _LOGGER.debug("%s handling push notification for namespace %s", self.__class__.__name__, namespace)
            payload = data['state']
            # The door opener state push notification contains an object for every channel handled by the
            # device.
            for door in payload:
                channel_index = door['channel']
                state = door['open'] == 1
                self.__garage_opener_open_state_by_channel[channel_index] = state
                locally_handled = True
        elif namespace == Namespace.GARAGE_DOOR_MULTIPLECONFIG:
            _LOGGER.debug("%s handling push notification for namespace %s", self.__class__.__name__, namespace)
            payload = data['config']
            # The door opener state push notification contains an object for every channel handled by the
            # device
            for door in payload:
                channel_index = door['channel']
                self.__garage_opener_config_state_by_channel[channel_index] = door
                locally_handled = True

        # Always call the parent handler when done with local specific logic. This gives the opportunity to all
        # ancestors to catch all events.
        parent_handled = await super()._async_handle_push_notification(namespace=namespace, data=data)
        return locally_handled or parent_handled

    async def async_handle_update(self, namespace: Namespace, data: dict) -> bool:
        """
        Handles data updates for the garage opener, such as from SYSTEM_ALL.
        :param namespace: Update namespace
        :param data: Update data
        :return: True if the mixin handled the update, False otherwise
        """
        _LOGGER.debug("Handling %s mixin data update.", self.__class__.__name__)
        locally_handled = False
        if namespace == Namespace.SYSTEM_ALL:
            doors_data = data.get('all', {}).get('digest', {}).get('garageDoor', [])
            for door in doors_data:
                channel_index = door['channel']
                state = door['open'] == 1
                self.__garage_opener_open_state_by_channel[channel_index] = state
            locally_handled = True

        super_handled = await super().async_handle_update(namespace=namespace, data=data)
        return super_handled or locally_handled

    async def async_garage_opener_fetch_config(self, *args, **kwargs) -> None:
        """
        Queries the device to fetch the GARAGE_DOOR_MULTIPLECONFIG.
        :return: None
        """
        data = await self._execute_command(method="GET", namespace=Namespace.GARAGE_DOOR_MULTIPLECONFIG, payload={})
        if 'config' in data:
            for door in data['config']:
                channel_index = door.get('channel')
                if channel_index is not None:
                    self.__garage_opener_config_state_by_channel[channel_index] = door

    async def async_garage_opener_set_config(self, channel: Optional[int] = None,
                                             door_enable: Optional[bool] = None,
                                             door_close_duration_mesec: Optional[int] = None,
                                             door_open_duration_mesec: Optional[int] = None,
                                             close_signal_mesec: Optional[int] = None,
                                             open_signal_mesec: Optional[int] = None,
                                             buzzer_enable: Optional[bool] = None
                                             , *args, **kwargs) -> None:
        """
        Configures the door device with specific parameters
        :param channel: Channel to configure
        :param door_enable: When true, enables the door. When false, disables it. Only useful with multi-door devices (e.g. msg200)
        :param door_close_duration_mesec:
        :param door_open_duration_mesec:
        :param close_signal_mesec:
        :param open_signal_mesec:
        :param buzzer_enable:
        :param args:
        :param kwargs:
        :return:
        """
        target_channel = self.__garage_opener_get_default_channel_index(channel)
        door_config = {"channel": target_channel}
        if door_enable is not None:
            door_config["doorEnable"] = 1 if door_enable else 0
        if door_close_duration_mesec is not None:
            door_config["doorCloseDuration"] = door_close_duration_mesec
        if door_open_duration_mesec is not None:
            door_config["doorOpenDuration"] = door_open_duration_mesec
        if close_signal_mesec is not None:
            door_config["signalClose"] = close_signal_mesec
        if open_signal_mesec is not None:
            door_config["signalOpen"] = open_signal_mesec
        if buzzer_enable is not None:
            door_config["buzzerEnable"] =  1 if buzzer_enable else 0
        payload = { "config": door_config }
        response_data = await self._execute_command(method="SET", namespace=Namespace.GARAGE_DOOR_MULTIPLECONFIG, payload=payload)
        self.__garage_opener_config_state_by_channel[target_channel].update(response_data)

    @ensure_full_update
    async def async_garage_opener_open(self, channel: Optional[int] = None, *args, **kwargs) -> None:
        """
        Operates the door: sends the open command.

        :param channel: channel to operate: defaults to 0
        :return: None
        """
        await self.__async_garage_opener_operate(state=True, channel=channel, *args, **kwargs)

    @ensure_full_update
    async def async_garage_opener_close(self, channel: Optional[int] = None, *args, **kwargs) -> None:
        """
        Operates the door: sends the close command.

        :param channel: channel to operate: defaults to 0
        :return: None
        """
        await self.__async_garage_opener_operate(state=False, channel=channel, *args, **kwargs)

    async def __async_garage_opener_operate(self,
                             state: bool,
                             channel: Optional[int] = None,
                             timeout: Optional[float] = None,
                             *args, **kwargs) -> None:
        target_channel = self.__garage_opener_get_default_channel_index(channel)
        payload = {"state": {"channel": target_channel, "open": 1 if state else 0, "uuid": self.uuid}}
        await self._execute_command(method="SET",
                                    namespace=Namespace.GARAGE_DOOR_STATE,
                                    payload=payload,
                                    timeout=timeout)

    @ensure_full_update
    def garage_opener_is_open(self, channel: Optional[int] = None, *args, **kwargs) -> Optional[bool]:
        """
        The current door-open status. Returns True if the given door is open, False otherwise.
        
        :param channel: channel of which status is needed
        :return: False if the door is closed, True otherwise
        """
        target_channel = self.__garage_opener_get_default_channel_index(channel)
        return self.__garage_opener_open_state_by_channel.get(target_channel)

    @ensure_full_update
    def garage_opener_get_config(self, channel: Optional[int] = None, *args, **kwargs) -> Optional[Dict]:
        """
        Returns the door configuration.
        
        :param channel: channel of which config is needed
        :return: dictionary containing the configuration variables, or None if the state is not known
        """
        target_channel = self.__garage_opener_get_default_channel_index(channel)
        config = self.__garage_opener_config_state_by_channel.get(target_channel)
        return config.copy() if config is not None else None

    def __garage_opener_get_default_channel_index(self, channel: Optional[int]) -> int:
        if channel is not None:
            return channel

        if len(self._channels)<2:
            return 0
        else:
            return 1
