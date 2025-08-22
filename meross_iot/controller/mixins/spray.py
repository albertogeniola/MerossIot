import logging
from typing import Optional

from meross_iot.controller.mixins.utilities import DynamicFilteringMixin
from meross_iot.model.enums import Namespace, SprayMode

_LOGGER = logging.getLogger(__name__)


class SprayMixin(DynamicFilteringMixin):
    _execute_command: callable
    check_full_update_done: callable
    #async_handle_update: Callable[[Namespace, dict], Awaitable]

    def __init__(self, device_uuid: str,
                 manager,
                 **kwargs):
        super().__init__(device_uuid=device_uuid, manager=manager, **kwargs)

        # Dictionary keeping the status for every channel
        self._channel_spray_status = {}

    @staticmethod
    def filter(device_ability : str, device_name : str,**kwargs):
        return device_ability == Namespace.CONTROL_SPRAY.value
    
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


        return locally_handled

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

        return locally_handled

    async def async_set_mode(self, mode: SprayMode, channel: int = 0, timeout: Optional[float] = None, *args, **kwargs) -> None:
        payload = {'spray': {'channel': channel, 'mode': mode.value}}
        await self._execute_command(method='SET',
                                    namespace=Namespace.CONTROL_SPRAY,
                                    payload=payload,
                                    timeout=timeout)
        # Immediately update local state
        self._channel_spray_status[channel] = mode
