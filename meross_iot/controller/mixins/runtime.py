import logging
from datetime import datetime
from typing import Optional

from meross_iot.controller.mixins.utilities import DynamicFilteringMixin
from meross_iot.model.enums import Namespace

_LOGGER = logging.getLogger(__name__)

_DATE_FORMAT = '%Y-%m-%d'


class SystemRuntimeMixin(DynamicFilteringMixin):
    _execute_command: callable

    def __init__(self, device_uuid: str,
                 manager,
                 **kwargs):
        super().__init__(device_uuid=device_uuid, manager=manager, **kwargs)
        self._runtime_info = {}

    @staticmethod
    def filter(device_ability : str, device_name : str,**kwargs):
        return device_ability == Namespace.SYSTEM_RUNTIME.value
    
    async def async_update_runtime_info(self, timeout: Optional[float] = None, *args, **kwargs) -> dict:
        """
        Polls the device to gather the latest runtime information for this device.
        Note that the returned value might vary with the time as Meross could add/remove/change runtime information
        in the future.

        :return: a `dict` object containing the runtime information provided by the Meross device
        """
        result = await self._execute_command(method="GET",
                                             namespace=Namespace.SYSTEM_RUNTIME,
                                             payload={},
                                             timeout=timeout)
        data = result.get('runtime')
        self._runtime_info = data
        return data

    @property
    def cached_system_runtime_info(self) -> Optional[dict]:
        """
        Returns the latest cached runtime info. If you want a fresh value, consider using the
        `update_runtime_info` method instead.
        """
        return self._runtime_info

    async def _async_request_update(self,
                           *args,
                           **kwargs) -> None:
        await self.async_update_runtime_info()
