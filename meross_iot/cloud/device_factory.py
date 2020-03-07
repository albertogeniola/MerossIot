import re

from meross_iot.cloud.devices.door_openers import GenericGarageDoorOpener
from meross_iot.cloud.devices.hubs import GenericHub
from meross_iot.cloud.devices.humidifier import GenericHumidifier
from meross_iot.cloud.devices.light_bulbs import GenericBulb
from meross_iot.cloud.devices.power_plugs import GenericPlug
from meross_iot.cloud.devices.subdevices.generic import GenericSubDevice
from meross_iot.cloud.devices.subdevices.sensors import SensorSubDevice
from meross_iot.cloud.devices.subdevices.thermostats import ValveSubDevice


def build_wrapper(
        cloud_client,
        device_type,  # type: str
        device_uuid,  # type: str
        device_specs  # type: dict
):
    if device_type.startswith('msl') or device_type.startswith('mss560m') or device_type.startswith('mss570m'):
        return GenericBulb(cloud_client, device_uuid=device_uuid, **device_specs)
    elif device_type.startswith('mss'):
        return GenericPlug(cloud_client, device_uuid=device_uuid, **device_specs)
    elif device_type.startswith('msg'):
        return GenericGarageDoorOpener(cloud_client, device_uuid=device_uuid, **device_specs)
    elif device_type.startswith('msh'):
        return GenericHub(cloud_client, device_uuid=device_uuid, **device_specs)
    elif device_type.startswith('msxh'):
        return GenericHumidifier(cloud_client, device_uuid=device_uuid, **device_specs)
    else:
        return GenericPlug(cloud_client, device_uuid=device_uuid, **device_specs)


def build_subdevice_wrapper(cloud_client,
                            device_type,  # type: str
                            device_id,  # type: str
                            device_specs,  # type: dict
                            parent_hub  # type: GenericHub
                            ):
    if device_type.startswith('mts'):
        return ValveSubDevice(cloud_client, subdevice_id=device_id, parent_hub=parent_hub, **device_specs)
    elif re.match('ms\d+', device_type, re.I):
        return SensorSubDevice(cloud_client, subdevice_id=device_id, parent_hub=parent_hub, **device_specs)
    else:
        return GenericSubDevice(cloud_client, subdevice_id=device_id, parent_hub=parent_hub, **device_specs)
