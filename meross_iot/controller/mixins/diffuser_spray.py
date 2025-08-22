import logging
from typing import Optional

from meross_iot.controller.mixins.utilities import DynamicFilteringMixin
from meross_iot.model.enums import Namespace, DiffuserSprayMode


_LOGGER = logging.getLogger(__name__)


class DiffuserSprayMixin(DynamicFilteringMixin):
    _execute_command: callable
    check_full_update_done: callable

    def __init__(self, device_uuid: str,
                 manager,
                 **kwargs):
        super().__init__(device_uuid=device_uuid, manager=manager, **kwargs)

        # Dictionary keeping the status for every channel
        self._channel_diffuser_spray_status = {}

    @staticmethod
    def filter(device_ability : str, device_name : str,**kwargs):
        return device_ability == Namespace.DIFFUSER_SPRAY.value
    
    async def async_handle_push_notification(self, namespace: Namespace, data: dict) -> bool:
        locally_handled = False

        if namespace == Namespace.DIFFUSER_SPRAY:
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
                    self._channel_diffuser_spray_status[channel] = c

                locally_handled = True

        return locally_handled

    async def async_handle_update(self, namespace: Namespace, data: dict) -> bool:
        _LOGGER.debug(f"Handling {self.__class__.__name__} mixin data update.")
        locally_handled = False
        if namespace == Namespace.SYSTEM_ALL:
            diffuser_data = data.get('all', {}).get('digest', {}).get('diffuser', {}).get('spray',[])
            for l in diffuser_data:
                channel = l['channel']
                self._channel_diffuser_spray_status[channel] = l
            locally_handled = True

        return locally_handled

    def get_current_spray_mode(self, channel: int = 0, *args, **kwargs) -> Optional[DiffuserSprayMode]:
        """
        Returns the current spray mode
        :param channel: channel to fetch info from
        :param args:
        :param kwargs:
        :return:
        """
        mode = self._channel_diffuser_spray_status.get(channel, {}).get('mode')
        if mode is not None:
            return DiffuserSprayMode(mode)
        return None

    async def async_set_spray_mode(self, mode: DiffuserSprayMode, channel: int = 0, timeout: Optional[float] = None, *args, **kwargs) -> None:
        """
        Changes the operating mode for this device
        :param mode: mode to set
        :param channel: channel to handle
        :param timeout: command timeout
        :return:
        """
        spray_payload = {"mode": mode.value, "channel": channel}
        payload = {'spray': [spray_payload]}
        await self._execute_command(method='SET',
                                    namespace=Namespace.DIFFUSER_SPRAY,
                                    payload=payload,
                                    timeout=timeout)
        # Immediately update local state
        self._channel_diffuser_spray_status[channel].update(spray_payload)
