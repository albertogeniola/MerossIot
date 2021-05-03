from meross_iot.controller.device import BaseDevice
from meross_iot.controller.mixins.roller_shutter import RollerShutterTimerMixin
from meross_iot.controller.mixins.system import SystemOnlineMixin, SystemAllMixin


class MRS100(SystemAllMixin, SystemOnlineMixin, RollerShutterTimerMixin, BaseDevice):
    """
    MRS100 Roller Shutter Timer
    """
    def __init__(self, device_uuid: str, manager, **kwargs):
        if 'channels' not in kwargs:
            kwargs['channels'] = [{}]
        super().__init__(device_uuid=device_uuid,
                         manager=manager,
                         **kwargs)
