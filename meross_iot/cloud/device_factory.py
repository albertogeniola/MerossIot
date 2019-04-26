from meross_iot.cloud.devices.power_plugs import GenericPlug
from meross_iot.cloud.devices.light_bulbs import GenericBulb


def build_wrapper(
        device_type,  # type: str
        device_specs  # type: dict
):
    if device_type.startswith('msl'):
        return GenericBulb(**device_specs)
    elif device_type.startswith('mss'):
        return GenericPlug(**device_specs)
    else:
        return GenericPlug(**device_specs)
