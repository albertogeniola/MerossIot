from meross_iot.supported_devices.power_plugs import Mss310, Mss110, Mss425e

def build_wrapper(
        token,
        key,
        user_id,
        device_type,  # type: str
        device_specs  # type: dict
):
    if device_type.lower() == "mss310":
        return Mss310(token, key, user_id,**device_specs)
    elif device_type.lower() == "mss110":
        return Mss110(token, key, user_id,**device_specs)
    elif device_type.lower() == "mss425e":
        return Mss425e(token, key, user_id,**device_specs)
    else:
        return None
