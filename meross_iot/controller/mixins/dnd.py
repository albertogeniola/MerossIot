import logging
from typing import Optional, Dict

from meross_iot.controller.mixins.utilities import DynamicFilteringMixin
from meross_iot.model.enums import Namespace, RollerShutterState, DNDMode

_LOGGER = logging.getLogger(__name__)


class SystemDndMixin(DynamicFilteringMixin):
    _execute_command: callable
    check_full_update_done: callable

    @staticmethod
    def filter(device_ability : str, device_name : str,**kwargs):
        return device_ability == Namespace.SYSTEM_DND_MODE.value
    ## It looks like the DND mode update/change does not trigger any PUSH notification update.
    ## This means we won't catch any "DND mode change" via push notifications.

    async def async_get_dnd_mode(self, timeout: Optional[float] = None, *args, **kwargs) -> DNDMode:
        """
        Polls the device and retrieves its DO-NOT-DISTURB mode.
        This method will actually refresh the cached DNDMode by issuing a MQTT message to the broker.
        You should avoid using this method when not strictly needed and cache the retrieved DND mode.
        :param timeout:
        :param args:
        :param kwargs:
        :return:
        """
        result = await self._execute_command(method="GET",
                                             namespace=Namespace.SYSTEM_DND_MODE,
                                             payload={},
                                             timeout=timeout)
        res = DNDMode(result['DNDMode']['mode'])
        return res

    async def set_dnd_mode(self, mode: DNDMode, timeout: Optional[float] = None, *args, **kwargs) -> None:
        """
        Controls the DND Mode setting on this device. When "Do not disturb" mode is enabled,
        the device will turn off its ambient led.
        :param mode:
        :param timeout:
        :param args:
        :param kwargs:
        :return:
        """
        await self._execute_command(method="SET",
                                             namespace=Namespace.SYSTEM_DND_MODE,
                                             payload={'DNDMode': {'mode': mode.value}},
                                             timeout=timeout)
