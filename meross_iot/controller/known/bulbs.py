from meross_iot.controller.device import BaseDevice
from meross_iot.controller.mixins.light import LightMixin
from meross_iot.controller.mixins.system import SystemAllMixin, SystemOnlineMixin
from meross_iot.controller.mixins.toggle import ToggleXMixin
from meross_iot.model.enums import Namespace


class MSL120(SystemAllMixin, SystemOnlineMixin, LightMixin, ToggleXMixin, BaseDevice):
    """
    MSL120 Smart Bulb
    """
    def __init__(self, device_uuid: str, manager, **kwargs):
        if 'channels' not in kwargs:
            kwargs['channels'] = [{}]

        # MSL120 has the following capacity
        custom_abilities = {Namespace.CONTROL_LIGHT.value: {'capacity': 7}}
        if hasattr(self, "_abilities_spec"):
            self._abilities_spec.update(custom_abilities)
        else:
            self._abilities_spec = custom_abilities

        super().__init__(device_uuid=device_uuid,
                         manager=manager,
                         **kwargs)


class MSL100(SystemAllMixin, SystemOnlineMixin, LightMixin, ToggleXMixin, BaseDevice):
    """
    MSL100 Smart Bulb
    """
    def __init__(self, device_uuid: str, manager, **kwargs):
        if 'channels' not in kwargs:
            kwargs['channels'] = [{}]
        super().__init__(device_uuid=device_uuid,
                         manager=manager,
                         **kwargs)

