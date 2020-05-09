from typing import Optional

from meross_iot.model.enums import Namespace


class GenericPushNotification(object):
    """Represents a generic push notification received from the Meross cloud"""
    def __init__(self,
                 namespace: Namespace,
                 originating_device_uuid: str,
                 raw_data: Optional[dict]):
        self.namespace = namespace
        self.originating_device_uuid = originating_device_uuid
        self.raw_data = raw_data
