from meross_iot.model.enums import Namespace, OnlineStatus
from meross_iot.model.push.common import HardwareInfo, FirmwareInfo, TimeInfo
from meross_iot.model.push.generic import GenericPushNotification


class OnlinePushNotification(GenericPushNotification):
    def __init__(self, originating_device_uuid: str, raw_data: dict):
        super().__init__(namespace=Namespace.SYSTEM_ONLINE,
                         originating_device_uuid=originating_device_uuid,
                         raw_data=raw_data)

    @property
    def status(self) -> OnlineStatus:
        return self.raw_data.get('online', {}).get('status', None)
