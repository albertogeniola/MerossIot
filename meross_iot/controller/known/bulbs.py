from meross_iot.controller.device import BaseDevice
from meross_iot.controller.mixins.light import LightMixin
from meross_iot.controller.mixins.toggle import ToggleXMixin


class MSL120(LightMixin, ToggleXMixin, BaseDevice):
    """
    MSL120 Smart Bulb
    """
    def __init__(self, device_uuid: str, manager, **kwargs):
        super().__init__(device_uuid=device_uuid,
                         manager=manager,
                         channels=[{}],  # Single channel bulb
                         **kwargs)


class MSL100(LightMixin, ToggleXMixin, BaseDevice):
    """
    MSL100 Smart Bulb
    """
    def __init__(self, device_uuid: str, manager, **kwargs):
        super().__init__(device_uuid=device_uuid,
                         manager=manager,
                         channels=[{}],  # Single channel bulb
                         **kwargs)

