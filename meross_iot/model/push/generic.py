from typing import Optional
from meross_iot.model.enums import Namespace
from abc import ABC, abstractmethod


class AbstractPushNotification(ABC):
    """Represents a generic push notification received from the Meross cloud"""
    def __init__(self,
                 namespace: Namespace,
                 originating_device_uuid: str,
                 raw_data: Optional[dict] = None):
        self.namespace = namespace
        self.originating_device_uuid = originating_device_uuid
        self._raw_data = raw_data

    @classmethod
    @abstractmethod
    def from_dict(cls, data: dict, originating_device_uuid: str):
        pass
