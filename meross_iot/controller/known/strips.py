from meross_iot.controller.device import BaseDevice
from meross_iot.controller.mixins.toggle import ToggleXMixin


class MSS420F(ToggleXMixin, BaseDevice):
    """
    MSS420F power strip
    """
    def __init__(self, device_uuid: str, manager, **kwargs):
        super().__init__(device_uuid=device_uuid,
                         manager=manager,
                         channels=[
                             {},  # Master channel
                             {},  # First switch
                             {},  # Second switch
                             {},  # Third switch
                             {},  # Fourth switch
                         ],
                         **kwargs)


class MSS425E(ToggleXMixin, BaseDevice):
    """
    MSS425E power strip
    """
    def __init__(self, device_uuid: str, manager, **kwargs):
        super().__init__(device_uuid=device_uuid,
                         manager=manager,
                         channels=[
                             {},  # Master channel
                             {},  # First switch
                             {},  # Second switch
                             {},  # Third switch
                             {
                                 'type': 'USB'
                             }  # USB switch
                         ],
                         **kwargs)


class MSS425F(ToggleXMixin, BaseDevice):
    """
    MSS425F power strip
    """
    def __init__(self, device_uuid: str, manager, **kwargs):
        super().__init__(device_uuid=device_uuid,
                         manager=manager,
                         channels=[
                             {},  # Master channel
                             {},  # First switch
                             {},  # Second switch
                             {},  # Third switch
                             {},  # Fourth switch
                             {
                                 'type': 'USB'
                             }  # USB switch
                         ],
                         **kwargs)


class MSS530(ToggleXMixin, BaseDevice):
    """
    MSS530 Multiple light control switches
    """

    def __init__(self, device_uuid: str, manager, **kwargs):
        super().__init__(device_uuid=device_uuid,
                         manager=manager,
                         channels=[
                             {},  # Master channel
                             {},  # First switch
                             {},  # Second switch
                             {},  # Third switch
                         ],  # Single channel bulb
                         **kwargs)
