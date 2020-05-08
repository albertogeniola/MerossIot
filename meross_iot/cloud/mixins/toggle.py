from typing import Optional

from meross_iot.model.enums import Namespace
from meross_iot.model.push.generic import GenericPushNotification
import logging


_LOGGER = logging.getLogger(__name__)


class ToggleXMixin(object):
    _execute_command: callable

    def __init__(self, device_uuid: str,
                 manager,
                 **kwargs):
        super().__init__(device_uuid=device_uuid, manager=manager, **kwargs)

        # _channel_status is a dictionary keeping the status for every channel
        self._channel_status = {}

    def handle_push_notification(self, push_notification: GenericPushNotification) -> bool:
        locally_handled = False

        if push_notification.namespace == Namespace.TOGGLEX:
            _LOGGER.debug(f"ToggleXMxin handling push notification for namespace {push_notification.namespace}")
            payload = push_notification.raw_data.get('togglex')
            if payload is None:
                _LOGGER.error(f"ToggleXMxin could not fine 'togglex' attribute in push notification data: {push_notification.raw_data}")
                locally_handled = False

            # The content of the togglex payload may vary. It can either be a dict (plugs with single switch)
            # or a list (power strips).
            elif isinstance(payload, list):
                for c in payload:
                    channel = c['channel']
                    switch_state = c['onoff'] == 1
                    self._channel_status[channel] = switch_state

            elif isinstance(payload, dict):
                channel = payload['channel']
                switch_state = payload['onoff'] == 1
                self._channel_status[channel] = switch_state

        # Always call the parent handler when done with local specific logic. This gives the opportunity to all
        # ancestors to catch all events.
        parent_handled = super().handle_push_notification(push_notification=push_notification)
        return locally_handled or parent_handled

    @property
    def is_on(self, channel=0, *args, **kwargs) -> Optional[bool]:
        return self._channel_status.get(channel, None)

    async def turn_off(self, channel=0, *args, **kwargs):
        await self._execute_command("SET", Namespace.TOGGLEX, {'togglex': {"onoff": 0, "channel": channel}})

    async def turn_on(self, channel=0, *args, **kwargs):
        await self._execute_command("SET", Namespace.TOGGLEX, {'togglex': {"onoff": 1, "channel": channel}})

    async def toggle(self, channel=0, *args, **kwargs):
        if self.is_on:
            await self.turn_off(channel=channel)
        else:
            await self.turn_on(channel=channel)


class ToggleMixin(object):
    _execute_command: callable

    def __init__(self, device_uuid: str,
                 manager,
                 **kwargs):
        super().__init__(device_uuid=device_uuid, manager=manager, **kwargs)

        # _channel_status is a dictionary keeping the status for every channel
        self._channel_status = {}

    def handle_push_notification(self, push_notification: GenericPushNotification) -> bool:
        locally_handled = False

        if push_notification.namespace == Namespace.TOGGLEX:
            _LOGGER.debug(f"ToggleMixin handling push notification for namespace {push_notification.namespace}")
            payload = push_notification.raw_data.get('togglex')
            if payload is None:
                _LOGGER.error(f"ToggleMixin could not fine 'toggle' attribute in push notification data: {push_notification.raw_data}")
                locally_handled = False

            else:
                channel_index = payload.get('channel', 0)
                switch_state = payload['onoff'] == 1
                self._channel_status[channel_index] = switch_state

        # Always call the parent handler when done with local specific logic. This gives the opportunity to all
        # ancestors to catch all events.
        parent_handled = super().handle_push_notification(push_notification=push_notification)
        return locally_handled or parent_handled

    @property
    def is_on(self, channel=0, *args, **kwargs) -> Optional[bool]:
        return self._channel_status.get(channel, None)

    async def turn_off(self, channel=0, *args, **kwargs):
        await self._execute_command("SET", Namespace.TOGGLE, {'toggle': {"onoff": 0, "channel": channel}})

    async def turn_on(self, channel=0, *args, **kwargs):
        await self._execute_command("SET", Namespace.TOGGLE, {'toggle': {"onoff": 1, "channel": channel}})

    async def toggle(self, channel=0, *args, **kwargs):
        if self.is_on:
            await self.turn_off(channel=channel)
        else:
            await self.turn_on(channel=channel)
