from typing import Protocol, Optional, Any, Dict

from meross_iot.model.enums import Namespace
from meross_iot.model.plugin.hub import BatteryInfo


class GenericSubDeviceProtocol(Protocol):
    def __init__(self, hubdevice_uuid: str, subdevice_id: str, status: int, last_active_time: int, manager, **kwargs):
        ...

    @property
    def internal_id(self) -> str:
        ...

    @property
    def subdevice_id(self) -> str:
        ...

    async def async_notify_hub_update(self, data: Dict) -> None:
        ...

    async def _execute_command(self, method: str, namespace: Namespace, payload: dict,
                               timeout: Optional[float] = None) -> dict:
        ...

    async def _async_handle_push_notification(self, namespace: str, data: Any) -> bool:
        ...


    def _prepare_push_notification_data(self, data: dict, filter_accessor: str = None) -> Optional[Dict]:
        ...
