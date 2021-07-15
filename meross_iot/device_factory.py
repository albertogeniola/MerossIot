import logging
from typing import Optional

from meross_iot.controller.device import BaseDevice, HubDevice, GenericSubDevice
from meross_iot.controller.known.bulbs import MSL120, MSL100
from meross_iot.controller.known.humidifiers import MSXH0
from meross_iot.controller.known.openers import MSG100
from meross_iot.controller.known.shutters import MRS100
from meross_iot.controller.known.plugs import MSS110, MSS210, MSS310, MSS620, MSS710
from meross_iot.controller.known.strips import MSS425E, MSS420F, MSS425F, MSS530
from meross_iot.controller.known.subdevice import Mts100v3Valve, Ms100Sensor
from meross_iot.controller.mixins.consumption import ConsumptionXMixin, ConsumptionMixin
from meross_iot.controller.mixins.electricity import ElectricityMixin
from meross_iot.controller.mixins.garage import GarageOpenerMixin
from meross_iot.controller.mixins.roller_shutter import RollerShutterTimerMixin
from meross_iot.controller.mixins.hub import HubMts100Mixin, HubMixn, HubMs100Mixin
from meross_iot.controller.mixins.light import LightMixin
from meross_iot.controller.mixins.spray import SprayMixin
from meross_iot.controller.mixins.system import SystemAllMixin, SystemOnlineMixin
from meross_iot.controller.mixins.toggle import ToggleXMixin, ToggleMixin
from meross_iot.model.enums import Namespace
from meross_iot.model.exception import UnknownDeviceType
from meross_iot.model.http.device import HttpDeviceInfo
from meross_iot.model.http.subdevice import HttpSubdeviceInfo

_LOGGER = logging.getLogger(__name__)

_KNOWN_DEV_TYPES_CLASSES = {
    "msl120": MSL120,
    "msl100": MSL100,
    "msxh0": MSXH0,
    "msg100": MSG100,
    "mrs100": MRS100,
    "mss110": MSS110,
    "mss210": MSS210,
    "mss310": MSS310,
    "mss620": MSS620,
    "mss710": MSS710,
    "msh300": HubDevice,
    "mss425e": MSS425E,
    "mss420f": MSS420F,
    "mss425f": MSS425F,
    "mss530": MSS530,
    "mts100v3": Mts100v3Valve,
    "ms100": Ms100Sensor
}

_ABILITY_MATRIX = {
    # Power plugs abilities
    Namespace.CONTROL_TOGGLEX.value: ToggleXMixin,
    Namespace.CONTROL_TOGGLE.value: ToggleMixin,
    Namespace.CONTROL_CONSUMPTIONX.value: ConsumptionXMixin,
    Namespace.CONTROL_CONSUMPTION.value: ConsumptionMixin,
    Namespace.CONTROL_ELECTRICITY.value: ElectricityMixin,

    # Light abilities
    Namespace.CONTROL_LIGHT.value: LightMixin,

    # Garage opener
    Namespace.GARAGE_DOOR_STATE.value: GarageOpenerMixin,

    # Roller shutter timer
    Namespace.ROLLER_SHUTTER_STATE.value: RollerShutterTimerMixin,

    # Spray opener
    Namespace.CONTROL_SPRAY.value: SprayMixin,

    # System
    Namespace.SYSTEM_ALL.value: SystemAllMixin,
    Namespace.SYSTEM_ONLINE.value: SystemOnlineMixin,

    # Hub
    Namespace.HUB_ONLINE.value: HubMixn,
    Namespace.HUB_TOGGLEX.value: HubMixn,

    Namespace.HUB_SENSOR_ALL.value: HubMs100Mixin,
    Namespace.HUB_SENSOR_ALERT.value: HubMs100Mixin,
    Namespace.HUB_SENSOR_TEMPHUM.value: HubMs100Mixin,

    Namespace.HUB_MTS100_ALL.value: HubMts100Mixin,
    Namespace.HUB_MTS100_MODE.value: HubMts100Mixin,
    Namespace.HUB_MTS100_TEMPERATURE.value: HubMts100Mixin

    # TODO: BIND, UNBIND, ONLINE, WIFI, ETC!
}

_SUBDEVICE_MAPPING = {
    "mts100v3": Mts100v3Valve,
    "ms100": Ms100Sensor
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
    lookup_string = _caclulate_device_type_name(device_type, hardware_version, firmware_version).strip(":")
    return _dynamic_types.get(lookup_string)


def _build_cached_type(type_string: str, device_abilities: dict, base_class: type) -> type:
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
        x_key = f"{key}X"
        x_version_ability = device_abilities.get(x_key)
        if x_version_ability is not None:
            clsx = _ABILITY_MATRIX.get(x_key)

        # Now, if we have both the clsx and the cls, prefer the clsx, otherwise go for the cls
        if clsx is not None:
            mixin_classes.add(clsx)
        elif cls is not None:
            mixin_classes.add(cls)

    # We must be careful when ordering the mixin and leaving the BaseMerossDevice as last class.
    # Messing up with that will cause MRO to not resolve inheritance correctly.
    mixin_classes = list(mixin_classes)
    mixin_classes.append(base_class)
    m = type(type_string, tuple(mixin_classes), {"_abilities_spec": device_abilities})
    return m


def build_meross_device_from_abilities(http_device_info: HttpDeviceInfo,
                                       device_abilities: dict,
                                       manager) -> BaseDevice:
    """
    Builds a managed meross device object given the specs reported by HTTP api and the abilities reported by the device
    itself.

    :param http_device_info:
    :param device_abilities:
    :param manager:
    :return:
    """
    # The current implementation of this library is based on the usage of pluggable Mixin classes on top of
    # a couple of base implementations.
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

        # Let's now pick the base class where to attach all the mixin.
        # We basically offer two possible base implementations:
        # - BaseMerossDevice: suitable for all non-hub devices
        # - HubMerossDevice: to be used when dealing with Hubs.
        # Unfortunately, it's not clear how we should discriminate an hub from a non-hub.
        # The current implementation decides which base class to use by looking at the presence
        # of 'Appliance.Digest.Hub' namespace within the exposed abilities.
        discriminating_ability = Namespace.SYSTEM_DIGEST_HUB.value
        base_class = BaseDevice
        if discriminating_ability in device_abilities:
            _LOGGER.warning(f"Device {http_device_info.dev_name} ({http_device_info.device_type}, "
                            f"uuid {http_device_info.uuid}) reported ability {discriminating_ability}. "
                            f"Assuming this is a full-featured HUB.")
            base_class = HubDevice

        cached_type = _build_cached_type(type_string=device_type_name,
                                         device_abilities=device_abilities,
                                         base_class=base_class)
        _dynamic_types[device_type_name] = cached_type

    component = cached_type(device_uuid=http_device_info.uuid, manager=manager, **http_device_info.to_dict())
    return component


def build_meross_device_from_known_types(http_device_info: HttpDeviceInfo,
                                         manager) -> BaseDevice:
    """
    Builds a managed meross device object by guess its relative class based on the device type string.
    Note that this method is capable of building managed device wrappers only if the device type is
    reported within the _KNOWN_DEV_TYPES_CLASSES. If your device type is not known yet, you should rely on
    `build_meross_device_from_abilities()` instead.

    :param http_device_info:
    :param manager:
    :return:
    """
    _LOGGER.debug(f"Building managed device for {http_device_info.dev_name} ({http_device_info.uuid}) "
                  f"from static known types ")
    dev_type = http_device_info.device_type.lower()
    target_clazz = _KNOWN_DEV_TYPES_CLASSES.get(dev_type)

    if target_clazz is None:
        _LOGGER.warning("Could not find any known device class for device type (%s).", http_device_info.device_type)
        raise UnknownDeviceType()

    return target_clazz(device_uuid=http_device_info.uuid, manager=manager, **http_device_info.to_dict())


def build_meross_subdevice(http_subdevice_info: HttpSubdeviceInfo, hub_uuid: str, hub_reported_abilities: dict,
                           manager) -> GenericSubDevice:
    _LOGGER.debug(f"Building managed device for {http_subdevice_info.sub_device_name} "
                  f"({http_subdevice_info.sub_device_id}).")

    # Build the device in accordance with the device type
    subdevtype = _SUBDEVICE_MAPPING.get(http_subdevice_info.sub_device_type)
    if subdevtype is None:
        _LOGGER.warning(f"Could not find any specific subdevice class for type {http_subdevice_info.sub_device_type}."
                        f" Applying generic SubDevice class.")
        subdevtype = GenericSubDevice
    return subdevtype(hubdevice_uuid=hub_uuid,
                      subdevice_id=http_subdevice_info.sub_device_id,
                      manager=manager,
                      **http_subdevice_info.to_dict())
