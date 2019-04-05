from meross_iot.supported_devices.power_plugs import GenericPlug
from meross_iot.supported_devices.plug_impl.mss425 import Mss425e


def build_wrapper(
        token,
        key,
        user_id,
        device_type,  # type: str
        device_specs  # type: dict
):
    if device_type.lower() == "mss425e":
        return Mss425e(token, key, user_id, **device_specs)
    else:
        return GenericPlug(token, key, user_id, **device_specs)
