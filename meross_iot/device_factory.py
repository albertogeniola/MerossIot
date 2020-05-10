import logging
from typing import Optional

from meross_iot.controller.mixins.consumption import ConsumptionXMixin
from meross_iot.controller.mixins.electricity import ElectricityMixin
from meross_iot.controller.mixins.garage import GarageOpenerMixin
from meross_iot.controller.mixins.light import LightMixin
from meross_iot.controller.mixins.spray import SprayMixin
from meross_iot.controller.mixins.system import SystemAllMixin, SystemOnlineMixin
from meross_iot.controller.mixins.toggle import ToggleXMixin, ToggleMixin
from meross_iot.model.device import BaseMerossDevice
from meross_iot.model.enums import Namespace
from meross_iot.model.http.device import HttpDeviceInfo

_LOGGER = logging.getLogger(__name__)


# TODO: implement logic to "selectively discard overlapping capabilities"
_ABILITY_MATRIX = {
    # Power plugs abilities
    Namespace.CONTROL_TOGGLEX.value: ToggleXMixin,
    Namespace.CONTROL_TOGGLE.value: ToggleMixin,
    Namespace.CONTROL_CONSUMPTIONX.value: ConsumptionXMixin,
    Namespace.CONTROL_ELECTRICITY.value: ElectricityMixin,

    # Light abilities
    Namespace.CONTROL_LIGHT.value: LightMixin,

    # Garage opener
    Namespace.GARAGE_DOOR_STATE.value: GarageOpenerMixin,

    # Spray opener
    Namespace.CONTROL_SPRAY.value: SprayMixin,

    # System
    Namespace.SYSTEM_ALL.value: SystemAllMixin,
    Namespace.SYSTEM_ONLINE.value: SystemOnlineMixin

    # TODO: BIND, UNBIND, ONLINE, WIFI, ETC!
}


_dynamic_types = {}


def _caclulate_device_type_name(device_type: str, hardware_version: str, firmware_version: str) -> str:
    """
    Calculates the name of the dynamic-type for a specific class of devices
    :param device_type:
    :param hardware_version:
    :param firmware_version:
    :return:
    """
    return f"{device_type}:{hardware_version}:{firmware_version}"


def _lookup_cached_type(device_type: str, hardware_version: str, firmware_version: str) -> Optional[type]:
    """
    Returns the cached dynamic type for the specific device, if any was already built for that one.
    :param device_type:
    :param hardware_version:
    :param firmware_version:
    :return:
    """
    lookup_string = _caclulate_device_type_name(device_type, hardware_version, firmware_version)
    return _dynamic_types.get(lookup_string)


def _build_cached_type(type_string: str, device_abilities: dict) -> type:
    """
    Builds a python type (class) dynamically by looking at the device abilities. In this way, we are able to
    "plugin" feature/mixins even for unknown new devices, given that they report abilities we already implemented.
    :param type_string:
    :param device_abilities:
    :return:
    """
    # Build a specific type at runtime by mixing plugins on-demand
    mixin_classes = set()

    # Add plugins by abilities
    for key, val in device_abilities.items():
        # When a device exposes the same ability like Tooggle and ToogleX, prefer the X version by filtering
        # out the non-X version.
        clsx = None
        cls = _ABILITY_MATRIX.get(key)

        # Check if for this ability the device exposes the X version
        x_version_ability_key = device_abilities.get(f"{key}X")
        if x_version_ability_key is not None:
            clsx = _ABILITY_MATRIX.get(x_version_ability_key)

        # Now, if we have both the clsx and the cls, prefer the clsx, otherwise go for the cls
        if clsx is not None:
            mixin_classes.add(clsx)
        elif cls is not None:
            mixin_classes.add(cls)

    # We must be careful when ordering the mixin and leaving the BaseMerossDevice as last class.
    # Messing up with that will cause MRO to not resolve inheritance correctly.
    mixin_classes = list(mixin_classes)
    mixin_classes.append(BaseMerossDevice)
    m = type(type_string, tuple(mixin_classes), {"_abilities_spec": device_abilities})
    return m


def build_meross_device(http_device_info: HttpDeviceInfo, device_abilities: dict, manager) -> BaseMerossDevice:
    """
    Builds a managed meross device object given the specs reported by HTTP api and the abilities reported by the device
    itself.
    :param http_device_info:
    :param device_abilities:
    :param manager:
    :return:
    """
    _LOGGER.debug(f"Building managed device for {http_device_info.dev_name} ({http_device_info.uuid}). "
                  f"Reported abilities: {device_abilities}")

    # Check if we already have cached type for that device kind.
    cached_type = _lookup_cached_type(http_device_info.device_type,
                                      http_device_info.hdware_version,
                                      http_device_info.fmware_version)
    if cached_type is None:
        _LOGGER.debug(f"Could not find any cached type for {http_device_info.device_type},"
                      f"{http_device_info.hdware_version},"
                      f"{http_device_info.fmware_version}. It will be generated.")
        device_type_name = _caclulate_device_type_name(http_device_info.device_type,
                                                       http_device_info.hdware_version,
                                                       http_device_info.fmware_version)
        cached_type = _build_cached_type(device_type_name, device_abilities)
        _dynamic_types[device_type_name] = cached_type

    component = cached_type(device_uuid=http_device_info.uuid, manager=manager, **http_device_info.to_dict())
    return component
