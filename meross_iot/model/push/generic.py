from typing import Optional
from meross_iot.model.enums import Namespace


class GenericPushNotification(object):
    """Represents a generic push notification received from the Meross cloud"""
    def __init__(self,
                 namespace: Namespace,
                 raw_data: Optional[dict] = None):
        self.namespace = namespace
        self._raw_data = raw_data
