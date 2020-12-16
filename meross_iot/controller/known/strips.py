from meross_iot.controller.device import BaseDevice
from meross_iot.controller.mixins.system import SystemOnlineMixin, SystemAllMixin
from meross_iot.controller.mixins.toggle import ToggleXMixin


class MSS420F(SystemAllMixin, SystemOnlineMixin, ToggleXMixin, BaseDevice):
    """
    MSS420F power strip
    """
    def __init__(self, device_uuid: str, manager, **kwargs):
        if 'channels' not in kwargs:
            kwargs['channels'] = [
                             {},  # Master channel
                             {},  # First switch
                             {},  # Second switch
                             {},  # Third switch
                             {},  # Fourth switch
                         ]
        super().__init__(device_uuid=device_uuid,
                         manager=manager,
                         **kwargs)


class MSS425E(SystemAllMixin, SystemOnlineMixin, ToggleXMixin, BaseDevice):
    """
    MSS425E power strip
    """
    def __init__(self, device_uuid: str, manager, **kwargs):
        if 'channels' not in kwargs:
            kwargs['channels'] = [
                             {},  # Master channel
                             {},  # First switch
                             {},  # Second switch
                             {},  # Third switch
                             {
                                 'type': 'USB'
                             }  # USB switch
                         ]
        super().__init__(device_uuid=device_uuid,
                         manager=manager,
                         **kwargs)


class MSS425F(SystemAllMixin, SystemOnlineMixin, ToggleXMixin, BaseDevice):
    """
    MSS425F power strip
    """
    def __init__(self, device_uuid: str, manager, **kwargs):
        if 'channels' not in kwargs:
            kwargs['channels'] = [
                             {},  # Master channel
                             {},  # First switch
                             {},  # Second switch
                             {},  # Third switch
                             {},  # Fourth switch
                             {
                                 'type': 'USB'
                             }  # USB switch
                         ]
        super().__init__(device_uuid=device_uuid,
                         manager=manager,
                         **kwargs)


class MSS530(SystemAllMixin, SystemOnlineMixin, ToggleXMixin, BaseDevice):
    """
    MSS530 Multiple light control switches
    """
    def __init__(self, device_uuid: str, manager, **kwargs):
        if 'channels' not in kwargs:
            kwargs['channels'] = [
                             {},  # Master channel
                             {},  # First switch
                             {},  # Second switch
                             {},  # Third switch
                         ]
        super().__init__(device_uuid=device_uuid,
                         manager=manager,
                         **kwargs)
