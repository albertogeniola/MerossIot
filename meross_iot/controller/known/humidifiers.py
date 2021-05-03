from meross_iot.controller.device import BaseDevice
from meross_iot.controller.mixins.light import LightMixin
from meross_iot.controller.mixins.spray import SprayMixin
from meross_iot.controller.mixins.system import SystemAllMixin, SystemOnlineMixin
from meross_iot.controller.mixins.toggle import ToggleXMixin


class MSXH0(SystemAllMixin, SystemOnlineMixin, SprayMixin, LightMixin, ToggleXMixin, BaseDevice):
    """
    MSXH0 Smart Humidifier devices
    """
    def __init__(self, device_uuid: str, manager, **kwargs):
        if 'channels' not in kwargs:
            kwargs['channels'] = [{}]
        super().__init__(device_uuid=device_uuid,
                         manager=manager,
                         **kwargs)
