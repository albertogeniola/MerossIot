from meross_iot.model.enums import Namespace
from meross_iot.model.push.common import HardwareInfo, FirmwareInfo, TimeInfo
from meross_iot.model.push.generic import GenericPushNotification


class BindPushNotification(GenericPushNotification):
    def __init__(self, hwinfo: HardwareInfo, fwinfo: FirmwareInfo, time: TimeInfo, originating_device_uuid: str, raw_data: dict):
        super().__init__(namespace=Namespace.CONTROL_BIND, originating_device_uuid=originating_device_uuid, raw_data=raw_data)
        self.hwinfo = hwinfo
        self.fwinfo = fwinfo
        self.time = time

    @classmethod
    def from_dict(cls, data: dict, originating_device_uuid: str):
        bind_data = data.get("bind")
        time = TimeInfo.from_dict(bind_data.get("time"))
        hardware = HardwareInfo.from_dict(bind_data.get("hardware"))
        firmware = HardwareInfo.from_dict(bind_data.get("hardware"))
        return BindPushNotification(hwinfo=hardware, fwinfo=firmware, time=time,
                                    originating_device_uuid=originating_device_uuid, raw_data=data)
