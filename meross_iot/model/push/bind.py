from meross_iot.model.enums import Namespace
from meross_iot.model.push.common import HardwareInfo, FirmwareInfo, TimeInfo
from meross_iot.model.push.generic import GenericPushNotification


class BindPushNotification(GenericPushNotification):
    def __init__(self, hwinfo: HardwareInfo, fwinfo: FirmwareInfo, time: TimeInfo):
        super().__init__(namespace=Namespace.BIND)
        self.hwinfo = hwinfo
        self.fwinfo = fwinfo
        self.time = time

    @classmethod
    def from_dict(cls, data: dict):
        bind_data = data.get("bind")
        time = TimeInfo.from_dict(bind_data.get("time"))
        hardware = HardwareInfo.from_dict(bind_data.get("hardware"))
        firmware = HardwareInfo.from_dict(bind_data.get("hardware"))
        return BindPushNotification(hwinfo=hardware, fwinfo=firmware, time=time)
