from meross_iot.controller.device import BaseDevice
from meross_iot.controller.mixins.garage import GarageOpenerMixin
from meross_iot.controller.mixins.system import SystemOnlineMixin, SystemAllMixin


class MSG100(SystemAllMixin, SystemOnlineMixin, GarageOpenerMixin, BaseDevice):
    """
    MSG100 Garage Opener
    """
    def __init__(self, device_uuid: str, manager, **kwargs):
        if 'channels' not in kwargs:
            kwargs['channels'] = [{}]
        super().__init__(device_uuid=device_uuid,
                         manager=manager,
                         **kwargs)
