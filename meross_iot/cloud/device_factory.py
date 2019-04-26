from meross_iot.cloud.devices.power_plugs import GenericPlug
from meross_iot.cloud.devices.light_bulbs import GenericBulb


def build_wrapper(
        cloud_client,
        device_type,        # type: str
        device_uuid,        # type: str
        device_specs        # type: dict
):
    if device_type.startswith('msl'):
        return GenericBulb(cloud_client, device_uuid=device_uuid, **device_specs)
    elif device_type.startswith('mss'):
        return GenericPlug(cloud_client, device_uuid=device_uuid, **device_specs)
    else:
        return GenericPlug(cloud_client, device_uuid=device_uuid, **device_specs)
