# This factory is maintained only for compatibility reasons.
# The current version of the library handles the logic via the GenericPlug class.

from meross_iot.supported_devices.power_plugs import GenericPlug


def build_wrapper(
        token,
        key,
        user_id,
        device_type,  # type: str
        device_specs  # type: dict
):
    return GenericPlug(token, key, user_id, **device_specs)
