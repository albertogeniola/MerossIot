import logging
from typing import Optional

from meross_iot.controller.device import BaseDevice
from meross_iot.model.enums import Namespace, DNDMode

_LOGGER = logging.getLogger(__name__)


class SystemDndMixin(BaseDevice):
    """
    Mixin for System DND (Do Not Disturb) functionality.
    """
    def __init__(self, device_uuid: str,
                 manager,
                 **kwargs):
        super().__init__(device_uuid=device_uuid, manager=manager, **kwargs)

    # Note: we are not overriding async_handle_update, as it seems the SYSTEM_ALL update
    #  does not carry information about DND mode.

    # Note: we are not overriding async_update, as we don't cache any local state for DND mode.

    # Note: we are not overriding _async_handle_push_notification, as it seems the DND mode update/change
    # does not trigger any PUSH notification update. This means we won't catch any "DND mode change" via push notifications.

    async def async_system_dnd_fetch_mode(self, timeout: Optional[float] = None, *args, **kwargs) -> DNDMode:
        """
        Polls the device and retrieves its DO-NOT-DISTURB mode.
        :param timeout:
        :return:
        """
        result = await self._execute_command(method="GET",
                                             namespace=Namespace.SYSTEM_DND_MODE,
                                             payload={},
                                             timeout=timeout)
        return DNDMode(result['DNDMode']['mode'])

    async def async_system_dnd_set_mode(self, mode: DNDMode, timeout: Optional[float] = None, *args, **kwargs) -> None:
        """
        Controls the DND Mode setting on this device. When "Do not disturb" mode is enabled,
        the device will turn off its ambient led.
        :param mode:
        :param timeout:
        :return:
        """
        await self._execute_command(method="SET",
                                    namespace=Namespace.SYSTEM_DND_MODE,
                                    payload={'DNDMode': {'mode': mode.value}},
                                    timeout=timeout)
