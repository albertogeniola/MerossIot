import logging
from typing import Optional

from meross_iot.model.enums import Namespace
from meross_iot.model.push.generic import GenericPushNotification

_LOGGER = logging.getLogger(__name__)


class ToggleXMixin(object):
    _execute_command: callable
    handle_update: callable

    def __init__(self, device_uuid: str,
                 manager,
                 **kwargs):
        super().__init__(device_uuid=device_uuid, manager=manager, **kwargs)

        # _channel_status is a dictionary keeping the status for every channel
        self._channel_togglex_status = {}

    def handle_push_notification(self, push_notification: GenericPushNotification) -> bool:
        locally_handled = False

        if push_notification.namespace == Namespace.TOGGLEX:
            _LOGGER.debug(f"ToggleXMxin handling push notification for namespace {push_notification.namespace}")
            payload = push_notification.raw_data.get('togglex')
            if payload is None:
                _LOGGER.error(f"ToggleXMxin could not find 'togglex' attribute in push notification data: {push_notification.raw_data}")

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
        parent_handled = super().handle_push_notification(push_notification=push_notification)
        return locally_handled or parent_handled

    def handle_update(self, data: dict) -> None:
        _LOGGER.debug(f"Handling {self.__class__.__name__} mixin data update.")
        payload = data.get('all', {}).get('digest', {}).get('togglex', [])
        for c in payload:
            channel = c['channel']
            switch_state = c['onoff'] == 1
            self._channel_togglex_status[channel] = switch_state
        super().handle_update(data=data)

    def is_on(self, channel=0, *args, **kwargs) -> Optional[bool]:
        return self._channel_togglex_status.get(channel, None)

    async def turn_off(self, channel=0, *args, **kwargs):
        await self._execute_command("SET", Namespace.TOGGLEX, {'togglex': {"onoff": 0, "channel": channel}})
        # Assume the command was ok, so immediately update the internal state
        self._channel_togglex_status[channel] = False

    async def turn_on(self, channel=0, *args, **kwargs):
        await self._execute_command("SET", Namespace.TOGGLEX, {'togglex': {"onoff": 1, "channel": channel}})
        # Assume the command was ok, so immediately update the internal state
        self._channel_togglex_status[channel] = True

    async def toggle(self, channel=0, *args, **kwargs):
        if self.is_on(channel=channel):
            await self.turn_off(channel=channel)
        else:
            await self.turn_on(channel=channel)


class ToggleMixin(object):
    _execute_command: callable
    handle_update: callable

    def __init__(self, device_uuid: str,
                 manager,
                 **kwargs):
        super().__init__(device_uuid=device_uuid, manager=manager, **kwargs)

        # _channel_status is a dictionary keeping the status for every channel
        self._channel_toggle_status = {}

    def handle_push_notification(self, push_notification: GenericPushNotification) -> bool:
        locally_handled = False

        if push_notification.namespace == Namespace.TOGGLEX:
            _LOGGER.debug(f"ToggleMixin handling push notification for namespace {push_notification.namespace}")
            payload = push_notification.raw_data.get('togglex')
            if payload is None:
                _LOGGER.error(f"ToggleMixin could not find 'toggle' attribute in push notification data: {push_notification.raw_data}")
            else:
                channel_index = payload.get('channel', 0)
                switch_state = payload['onoff'] == 1
                self._channel_toggle_status[channel_index] = switch_state
                locally_handled = True

        # Always call the parent handler when done with local specific logic. This gives the opportunity to all
        # ancestors to catch all events.
        parent_handled = super().handle_push_notification(push_notification=push_notification)
        return locally_handled or parent_handled

    def handle_update(self, data: dict) -> None:
        _LOGGER.debug(f"Handling {self.__class__.__name__} mixin data update.")
        payload = data.get('all', {}).get('control', {}).get('toggle', {})
        channel_index = payload.get('channel', 0)
        switch_state = payload['onoff'] == 1
        self._channel_toggle_status[channel_index] = switch_state
        super().handle_update(data=data)

    def is_on(self, channel=0, *args, **kwargs) -> Optional[bool]:
        return self._channel_toggle_status.get(channel, None)

    async def turn_off(self, channel=0, *args, **kwargs):
        await self._execute_command("SET", Namespace.TOGGLE, {'toggle': {"onoff": 0, "channel": channel}})

    async def turn_on(self, channel=0, *args, **kwargs):
        await self._execute_command("SET", Namespace.TOGGLE, {'toggle': {"onoff": 1, "channel": channel}})

    async def toggle(self, channel=0, *args, **kwargs):
        if self.is_on(channel=channel):
            await self.turn_off(channel=channel)
        else:
            await self.turn_on(channel=channel)
