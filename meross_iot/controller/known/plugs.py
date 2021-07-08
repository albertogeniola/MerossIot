from meross_iot.controller.device import BaseDevice
from meross_iot.controller.mixins.consumption import ConsumptionXMixin
from meross_iot.controller.mixins.electricity import ElectricityMixin
from meross_iot.controller.mixins.system import SystemOnlineMixin, SystemAllMixin
from meross_iot.controller.mixins.toggle import ToggleMixin, ToggleXMixin


class MSS110(SystemAllMixin, SystemOnlineMixin, ToggleMixin, BaseDevice):
    """
    MSS110 smart plug
    """
    def __init__(self, device_uuid: str, manager, **kwargs):
        if 'channels' not in kwargs:
            kwargs['channels'] = [{}]
        super().__init__(device_uuid=device_uuid,
                         manager=manager,
                         **kwargs)


class MSS210(SystemAllMixin, SystemOnlineMixin, ToggleXMixin, BaseDevice):
    """
    MSS210 smart plug
    """
    def __init__(self, device_uuid: str, manager, **kwargs):
        if 'channels' not in kwargs:
            kwargs['channels'] = [{}]
        super().__init__(device_uuid=device_uuid,
                         manager=manager,
                         **kwargs)


class MSS310(SystemAllMixin, SystemOnlineMixin, ConsumptionXMixin, ElectricityMixin, ToggleXMixin, BaseDevice):
    """
    MSS310 device with electricity/power consumption reading
    """
    def __init__(self, device_uuid: str, manager, **kwargs):
        if 'channels' not in kwargs:
            kwargs['channels'] = [{}]
        super().__init__(device_uuid=device_uuid,
                         manager=manager,
                         **kwargs)


class MSS620(SystemAllMixin, SystemOnlineMixin, ToggleXMixin, BaseDevice):
    """
    MSS710 device
    """
    def __init__(self, device_uuid: str, manager, **kwargs):
        if 'channels' not in kwargs:
            kwargs['channels'] = [{}]
        super().__init__(device_uuid=device_uuid,
                         manager=manager,
                         **kwargs)

class MSS710(SystemAllMixin, SystemOnlineMixin, ToggleXMixin, BaseDevice):
    """
    MSS710 device
    """
    def __init__(self, device_uuid: str, manager, **kwargs):
        if 'channels' not in kwargs:
            kwargs['channels'] = [{}]
        super().__init__(device_uuid=device_uuid,
                         manager=manager,
                         **kwargs)
