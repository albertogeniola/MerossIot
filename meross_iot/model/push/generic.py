from typing import Optional, Dict
from meross_iot.model.enums import Namespace


class GenericPushNotification(object):
    """Represents a generic push notification received from the Meross cloud"""
    def __init__(self,
                 namespace: Namespace,
                 originating_device_uuid: str,
                 raw_data: Optional[Dict]):
        self._namespace = namespace
        self._originating_device_uuid = originating_device_uuid
        self._raw_data = raw_data

    @property
    def namespace(self) -> Namespace:
        return self._namespace

    @property
    def originating_device_uuid(self) -> str:
        return self._originating_device_uuid

    @property
    def subdevice_id(self) -> Optional[str]:
        """
        Push notification referring to SubDevices will override this method.
        Can be None if the PushNotification is not related to a SubDevice
        :return:
        """
        return None

    @property
    def raw_data(self) -> Dict:
        return self._raw_data
