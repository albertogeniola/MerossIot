from meross_iot.model.enums import Namespace
from meross_iot.model.push.common import HardwareInfo, FirmwareInfo, TimeInfo
from meross_iot.model.push.generic import GenericPushNotification


class BindPushNotification(GenericPushNotification):
    def __init__(self, originating_device_uuid: str, raw_data: dict):
        super().__init__(namespace=Namespace.CONTROL_BIND,
                         originating_device_uuid=originating_device_uuid,
                         raw_data=raw_data)

    @property
    def time(self) -> TimeInfo:
        return TimeInfo.from_dict(self.raw_data.get("bind").get("time"))

    @property
    def hwinfo(self) -> HardwareInfo:
        return TimeInfo.from_dict(self.raw_data.get("bind").get("hardware"))

    @property
    def fwinfo(self) -> FirmwareInfo:
        return TimeInfo.from_dict(self.raw_data.get("bind").get("firmware"))

