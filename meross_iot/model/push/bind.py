from meross_iot.model.enums import Namespace
from meross_iot.model.push.common import HardwareInfo, FirmwareInfo, TimeInfo
from meross_iot.model.push.generic import AbstractPushNotification


class BindPushNotification(AbstractPushNotification):
    def __init__(self, hwinfo: HardwareInfo, fwinfo: FirmwareInfo, time: TimeInfo, originating_device_uuid: str):
        super().__init__(namespace=Namespace.BIND, originating_device_uuid=originating_device_uuid)
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
                                    originating_device_uuid=originating_device_uuid)
