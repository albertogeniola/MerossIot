from meross_iot.supported_devices.power_plug_impl.mss110 import Mss110
from meross_iot.supported_devices.power_plug_impl.mss210 import Mss210
from meross_iot.supported_devices.power_plug_impl.mss310 import Mss310
from meross_iot.supported_devices.power_plug_impl.mss425 import Mss425e


def build_wrapper(
        token,
        key,
        user_id,
        device_type,  # type: str
        device_specs  # type: dict
):
    if device_type.lower() == "mss310":
        return Mss310(token, key, user_id, **device_specs)
    # Beta support for mss310h using the Mss310
    elif device_type.lower() == "mss310h":
        return Mss310(token, key, user_id, **device_specs)
    elif device_type.lower() == "mss210":
        return Mss210(token, key, user_id, **device_specs)
    elif device_type.lower() == "mss110":
        return Mss110(token, key, user_id, **device_specs)
    elif device_type.lower() == "mss425e":
        return Mss425e(token, key, user_id, **device_specs)
    else:
        return None
