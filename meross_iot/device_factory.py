# This factory is maintained only for compatibility reasons.
# The current version of the library handles the logic via the GenericPlug class.

from meross_iot.supported_devices.power_plugs import GenericPlug
from meross_iot.supported_devices.light_bulbs import GenericBulb


def build_wrapper(
        token,
        key,
        user_id,
        device_type,  # type: str
        device_specs  # type: dict
):
    # The MSS560 is a dimmerable switch, therefore we consider it as a bulb.
    if device_type.startswith('mss560'):
        return GenericBulb(token, key, user_id, **device_specs)
    elif device_type.startswith('msl'):
        return GenericBulb(token, key, user_id, **device_specs)
    elif device_type.startswith('mss'):
        return GenericPlug(token, key, user_id, **device_specs)
    else:
        return GenericPlug(token, key, user_id, **device_specs)
