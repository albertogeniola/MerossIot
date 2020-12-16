import logging
from typing import Optional

from meross_iot.model.enums import Namespace

_LOGGER = logging.getLogger(__name__)


class ToggleXMixin(object):
    """
    This mixin is implemented by devices that support ToggleX operation, such as smart switches
    and smart bulbs.
    """
    _execute_command: callable
    check_full_update_done: callable
    #async_handle_update: Callable[[Namespace, dict], Awaitable]

    def __init__(self, device_uuid: str,
                 manager,
                 **kwargs):
        super().__init__(device_uuid=device_uuid, manager=manager, **kwargs)

        # _channel_status is a dictionary keeping the status for every channel
        self._channel_togglex_status = {}

    async def async_handle_push_notification(self, namespace: Namespace, data: dict) -> bool:
        locally_handled = False

        if namespace == Namespace.CONTROL_TOGGLEX:
            _LOGGER.debug(f"{self.__class__.__name__} handling push notification for namespace {namespace}")
            payload = data.get('togglex')
            if payload is None:
                _LOGGER.error(f"{self.__class__.__name__} could not find 'togglex' attribute in push notification data: {data}")

            # The content of the togglex payload may vary. It can either be a dict (plugs with single switch)
            # or a list (power strips).
            elif isinstance(payload, list):
                for c in payload:
                    channel = c['channel']
                    switch_state = c['onoff'] == 1
                    self._channel_togglex_status[channel] = switch_state
                    locally_handled = True

            elif isinstance(payload, dict):
                channel = payload['channel']
                switch_state = payload['onoff'] == 1
                self._channel_togglex_status[channel] = switch_state
                locally_handled = True

        # Always call the parent handler when done with local specific logic. This gives the opportunity to all
        # ancestors to catch all events.
        parent_handled = await super().async_handle_push_notification(namespace=namespace, data=data)
        return locally_handled or parent_handled

    async def async_handle_update(self, namespace: Namespace, data: dict) -> bool:
        _LOGGER.debug(f"Handling {self.__class__.__name__} mixin data update.")
        locally_handled = False
        if namespace == Namespace.SYSTEM_ALL:
            payload = data.get('all', {}).get('digest', {}).get('togglex', [])
            for c in payload:
                channel = c['channel']
                switch_state = c['onoff'] == 1
                self._channel_togglex_status[channel] = switch_state
            locally_handled = True

        super_handled = await super().async_handle_update(namespace=namespace, data=data)
        return super_handled or locally_handled

    def is_on(self, channel=0, *args, **kwargs) -> Optional[bool]:
        """
        Returns the ON/OFF state of the switch channel.

        :param channel: channel index of interested. Defaults to 0

        :return: True is the stat is ON, False when it's OFF
        """
        self.check_full_update_done()
        return self._channel_togglex_status.get(channel, None)

    async def async_turn_off(self, channel=0, skip_rate_limits: bool = False, drop_on_overquota: bool = True, *args, **kwargs) -> None:
        """
        Turns off the specified channel of the device

        :param channel: channel index to turn off. Defaults to 0.

        :return: None
        """
        await self._execute_command(method="SET",
                                    namespace=Namespace.CONTROL_TOGGLEX,
                                    payload={'togglex': {"onoff": 0, "channel": channel}},
                                    skip_rate_limits=skip_rate_limits,
                                    drop_on_overquota=drop_on_overquota)

        # Assume the command was ok, so immediately update the internal state
        self._channel_togglex_status[channel] = False

    async def async_turn_on(self, channel=0, skip_rate_limits: bool = False, drop_on_overquota: bool = True, *args, **kwargs) -> None:
        """
        Turns on the specified channel of the device

        :param channel: channel index to turn on. Defaults to 0.
        :param channel:

        :return: None
        """
        await self._execute_command(method="SET",
                                    namespace=Namespace.CONTROL_TOGGLEX,
                                    payload={'togglex': {"onoff": 1, "channel": channel}},
                                    skip_rate_limits=skip_rate_limits,
                                    drop_on_overquota=drop_on_overquota)
        # Assume the command was ok, so immediately update the internal state
        self._channel_togglex_status[channel] = True

    async def async_toggle(self, channel=0, *args, **kwargs) -> None:
        """
        Toggles the switch status of the specified channel

        :param channel: channel index to toggle. Defaults to 0.

        :return: None
        """
        if self.is_on(channel=channel):
            await self.async_turn_off(channel=channel)
        else:
            await self.async_turn_on(channel=channel)


class ToggleMixin(object):
    _execute_command: callable
    #async_handle_update: Callable[[Namespace, dict], Awaitable]

    def __init__(self, device_uuid: str,
                 manager,
                 **kwargs):
        super().__init__(device_uuid=device_uuid, manager=manager, **kwargs)

        # _channel_status is a dictionary keeping the status for every channel
        self._channel_toggle_status = {}

    async def async_handle_push_notification(self, namespace: Namespace, data: dict) -> bool:
        locally_handled = False

        if namespace == Namespace.CONTROL_TOGGLE:
            _LOGGER.debug(f"ToggleMixin handling push notification for namespace {namespace}")
            payload = data.get('toggle')
            if payload is None:
                _LOGGER.error(f"ToggleMixin could not find 'toggle' attribute in push notification data: {data}")
            else:
                channel_index = payload.get('channel', 0)
                switch_state = payload['onoff'] == 1
                self._channel_toggle_status[channel_index] = switch_state
                locally_handled = True

        # Always call the parent handler when done with local specific logic. This gives the opportunity to all
        # ancestors to catch all events.
        parent_handled = await super().async_handle_push_notification(namespace=namespace, data=data)
        return locally_handled or parent_handled

    async def async_handle_update(self, namespace: Namespace, data: dict) -> bool:
        _LOGGER.debug(f"Handling {self.__class__.__name__} mixin data update.")
        locally_handled = False
        if namespace == Namespace.SYSTEM_ALL:
            payload = data.get('all', {}).get('control', {}).get('toggle', {})
            channel_index = payload.get('channel', 0)
            switch_state = payload['onoff'] == 1
            self._channel_toggle_status[channel_index] = switch_state
            locally_handled = True
        super_handled = await super().async_handle_update(namespace=namespace, data=data)
        return super_handled or locally_handled

    def is_on(self, channel=0, *args, **kwargs) -> Optional[bool]:
        self.check_full_update_done()
        return self._channel_toggle_status.get(channel, None)

    async def async_turn_off(self, channel=0, skip_rate_limits: bool = False, drop_on_overquota: bool = True, *args, **kwargs) -> None:
        await self._execute_command(method="SET",
                                    namespace=Namespace.CONTROL_TOGGLE,
                                    payload={'toggle': {"onoff": 0, "channel": channel}},
                                    skip_rate_limits=skip_rate_limits,
                                    drop_on_overquota=drop_on_overquota)
        # Assume the command was ok, so immediately update the internal state
        self._channel_toggle_status[channel] = False

    async def async_turn_on(self, channel=0, skip_rate_limits: bool = False, drop_on_overquota: bool = True, *args, **kwargs) -> None:
        await self._execute_command(method="SET",
                                    namespace=Namespace.CONTROL_TOGGLE,
                                    payload={'toggle': {"onoff": 1, "channel": channel}},
                                    skip_rate_limits=skip_rate_limits,
                                    drop_on_overquota=drop_on_overquota)
        # Assume the command was ok, so immediately update the internal state
        self._channel_toggle_status[channel] = True

    async def async_toggle(self, channel=0, *args, **kwargs) -> None:
        if self.is_on(channel=channel):
            await self.async_turn_off(channel=channel)
        else:
            await self.async_turn_on(channel=channel)
