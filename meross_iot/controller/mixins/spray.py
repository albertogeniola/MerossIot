import logging
from typing import Optional

from meross_iot.model.enums import Namespace, SprayMode

_LOGGER = logging.getLogger(__name__)


class SprayMixin(object):
    _execute_command: callable
    check_full_update_done: callable
    #async_handle_update: Callable[[Namespace, dict], Awaitable]

    def __init__(self, device_uuid: str,
                 manager,
                 **kwargs):
        super().__init__(device_uuid=device_uuid, manager=manager, **kwargs)

        # Dictionary keeping the status for every channel
        self._channel_spray_status = {}

    async def async_handle_push_notification(self, namespace: Namespace, data: dict) -> bool:
        locally_handled = False

        if namespace == Namespace.CONTROL_SPRAY:
            _LOGGER.debug(f"{self.__class__.__name__} handling push notification for namespace {namespace}")
            payload = data.get('spray')
            if payload is None:
                _LOGGER.error(f"{self.__class__.__name__} could not find 'spray' attribute in push notification data: "
                              f"{data}")
                locally_handled = False
            else:
                # Update the status of every channel that has been reported in this push
                # notification.
                for c in payload:
                    channel = c['channel']
                    strmode = c['mode']
                    mode = SprayMode(strmode)
                    self._channel_spray_status[channel] = mode

                locally_handled = True

        # Always call the parent handler when done with local specific logic. This gives the opportunity to all
        # ancestors to catch all events.
        parent_handled = await super().async_handle_push_notification(namespace=namespace, data=data)
        return locally_handled or parent_handled

    def get_current_mode(self, channel: int = 0, *args, **kwargs) -> Optional[SprayMode]:
        self.check_full_update_done()
        return self._channel_spray_status.get(channel)

    async def async_handle_update(self, namespace: Namespace, data: dict) -> bool:
        _LOGGER.debug(f"Handling {self.__class__.__name__} mixin data update.")
        locally_handled = False
        if namespace == Namespace.SYSTEM_ALL:
            spray_data = data.get('all', {}).get('digest', {}).get('spray', [])
            for c in spray_data:
                channel = c['channel']
                strmode = c['mode']
                mode = SprayMode(strmode)
                self._channel_spray_status[channel] = mode
            locally_handled = True

        super_handled = await super().async_handle_update(namespace=namespace, data=data)
        return super_handled or locally_handled

    async def async_set_mode(self, mode: SprayMode, channel: int = 0, skip_rate_limits: bool = False, drop_on_overquota: bool = True, *args, **kwargs) -> None:
        payload = {'spray': {'channel': channel, 'mode': mode.value}}
        await self._execute_command(method='SET',
                                    namespace=Namespace.CONTROL_SPRAY,
                                    payload=payload,
                                    skip_rate_limits=skip_rate_limits,
                                    drop_on_overquota=drop_on_overquota)
        # Immediately update local state
        self._channel_spray_status[channel] = mode
