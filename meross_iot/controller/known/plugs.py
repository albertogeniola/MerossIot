from meross_iot.controller.device import BaseDevice
from meross_iot.controller.mixins.electricity import ElectricityMixin
from meross_iot.controller.mixins.toggle import ToggleMixin, ToggleXMixin


class MSS110(ToggleMixin, BaseDevice):
    """
    MSS110 smart plug
    """
    def __init__(self, device_uuid: str, manager, **kwargs):
        super().__init__(device_uuid=device_uuid,
                         manager=manager,
                         channels=[{}],  # Single channel plug
                         **kwargs)


class MSS210(ToggleXMixin, BaseDevice):
    """
    MSS210 smart plug
    """
    def __init__(self, device_uuid: str, manager, **kwargs):
        super().__init__(device_uuid=device_uuid,
                         manager=manager,
                         channels=[{}],  # Single channel plug
                         **kwargs)


class MSS310(ElectricityMixin, ToggleXMixin, BaseDevice):
    """
    MSS310 device with electricity/power consumption reading
    """
    def __init__(self, device_uuid: str, manager, **kwargs):
        super().__init__(device_uuid=device_uuid,
                         manager=manager,
                         channels=[{}],  # Single channel plug
                         **kwargs)


class MSS710(ToggleXMixin, BaseDevice):
    """
    MSS710 device
    """
    def __init__(self, device_uuid: str, manager, **kwargs):
        super().__init__(device_uuid=device_uuid,
                         manager=manager,
                         channels=[{}],  # Single channel plug
                         **kwargs)
