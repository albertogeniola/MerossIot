import logging
from typing import Optional, Dict

from meross_iot.controller.device import BaseDevice, GenericSubDevice
from meross_iot.controller.mixins.alarm import AlarmMixin
from meross_iot.controller.mixins.consumption import ConsumptionXMixin, ConsumptionMixin
from meross_iot.controller.mixins.diffuser_light import DiffuserLightMixin
from meross_iot.controller.mixins.diffuser_spray import DiffuserSprayMixin
from meross_iot.controller.mixins.dnd import SystemDndMixin
from meross_iot.controller.mixins.electricity import ElectricityMixin
from meross_iot.controller.mixins.encryption import EncryptionSuiteMixin
from meross_iot.controller.mixins.garage import GarageOpenerMixin
from meross_iot.controller.mixins.hub import HubMixin
from meross_iot.controller.mixins.light import LightMixin
from meross_iot.controller.mixins.roller_shutter import RollerShutterTimerMixin
from meross_iot.controller.mixins.runtime import SystemRuntimeMixin
from meross_iot.controller.mixins.spray import SprayMixin
from meross_iot.controller.mixins.system import SystemAllMixin, SystemOnlineMixin
from meross_iot.controller.mixins.thermostat import ThermostatModeMixin, ThermostatModeBMixin
from meross_iot.controller.mixins.toggle import ToggleXMixin, ToggleMixin
from meross_iot.controller.subdevice_mixins.door_window import DoorWindowSensorMixin
from meross_iot.controller.subdevice_mixins.leakage_sensor import LeakageSensorMixin
from meross_iot.controller.subdevice_mixins.ms100_sensor import Ms100Mixin
from meross_iot.controller.subdevice_mixins.hub_togglex import ToggleXSensorMixin
from meross_iot.controller.subdevice_mixins.mts100_thermostat import Mts100Mixin
from meross_iot.model.enums import Namespace
from meross_iot.model.exception import UnknownDeviceType
from meross_iot.model.http.device import HttpDeviceInfo

_LOGGER = logging.getLogger(__name__)

_KNOWN_DEV_TYPES_CLASSES = {}

_ABILITY_MATRIX = {
    # Power plugs abilities
    Namespace.CONTROL_TOGGLEX.value: ToggleXMixin,
    Namespace.CONTROL_TOGGLE.value: ToggleMixin,
    Namespace.CONTROL_CONSUMPTIONX.value: ConsumptionXMixin,
    Namespace.CONTROL_CONSUMPTION.value: ConsumptionMixin,
    Namespace.CONTROL_ELECTRICITY.value: ElectricityMixin,
    Namespace.CONTROL_ALARM.value: AlarmMixin,

    # Encryption
    Namespace.SYSTEM_ENCRYPTION.value: EncryptionSuiteMixin,

    # Light abilities
    Namespace.CONTROL_LIGHT.value: LightMixin,

    # Garage opener
    Namespace.GARAGE_DOOR_STATE.value: GarageOpenerMixin,

    # Roller shutter timer
    Namespace.ROLLER_SHUTTER_STATE.value: RollerShutterTimerMixin,

    # Spray
    Namespace.CONTROL_SPRAY.value: SprayMixin,

    # Oil diffuser
    Namespace.DIFFUSER_LIGHT.value: DiffuserLightMixin,
    Namespace.DIFFUSER_SPRAY.value: DiffuserSprayMixin,

    # System
    Namespace.SYSTEM_ALL.value: SystemAllMixin,
    Namespace.SYSTEM_ONLINE.value: SystemOnlineMixin,
    Namespace.SYSTEM_RUNTIME.value: SystemRuntimeMixin,

    # Hub
    Namespace.HUB_SUBDEVICELIST.value: HubMixin,
    Namespace.HUB_ONLINE.value: HubMixin,
    Namespace.HUB_BATTERY.value: HubMixin,
    Namespace.HUB_TOGGLEX.value: HubMixin,

    Namespace.HUB_SENSOR_ALL.value: HubMixin,
    Namespace.HUB_SENSOR_ALERT.value: HubMixin,
    Namespace.HUB_SENSOR_TEMPHUM.value: HubMixin,

    Namespace.HUB_MTS100_ALL.value: HubMixin,
    Namespace.HUB_MTS100_MODE.value: HubMixin,
    Namespace.HUB_MTS100_TEMPERATURE.value: HubMixin,

    # DND
    Namespace.SYSTEM_DND_MODE.value: SystemDndMixin,

    # Thermostat
    Namespace.CONTROL_THERMOSTAT_MODE.value: ThermostatModeMixin,
    Namespace.CONTROL_THERMOSTAT_MODEB.value: ThermostatModeBMixin,

    # TODO: BIND, UNBIND, ONLINE, WIFI, ETC!
}

_SUB_DEVICE_MIXIN_MAP = {
    "mts100": Mts100Mixin,
    "ms100": Ms100Mixin,

    "waterLeak": LeakageSensorMixin,
    "doorWindow": DoorWindowSensorMixin,

    "togglex": ToggleXSensorMixin,
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

        cached_type = _build_cached_type(type_string=device_type_name,
                                         device_abilities=device_abilities,
                                         base_class=BaseDevice)
        _dynamic_types[device_type_name] = cached_type

    #component = cached_type(device_uuid=http_device_info.uuid, manager=manager, **http_device_info.to_dict())
    component = cached_type(device_uuid=http_device_info.uuid, manager=manager, http_device_info=http_device_info)
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
        _LOGGER.debug("Could not find any known device class for device type (%s).", http_device_info.device_type)
        raise UnknownDeviceType()

    return target_clazz(device_uuid=http_device_info.uuid, manager=manager, **http_device_info.to_dict())


def build_subdevice_from_digest_payload(hub_device: HubMixin, digest_payload: Dict, version_payload: Optional[Dict]) -> GenericSubDevice:
    """Builds a managed meross SubDevice instance, starting from the digest payload obtained by via the hub"""
    subdevice_id = digest_payload.get('id')
    status = digest_payload.get('status')
    last_active_time = digest_payload.get('lastActiveTime')
    _LOGGER.debug(f"Building managed SubDevice {subdevice_id} (hub {hub_device.name} - {hub_device.uuid}) ")

    # We build the device abilities via SubdeviceMixins, based digest keys, handled statically.
    mixin_classes = []
    for k in digest_payload:
        mixin = _SUB_DEVICE_MIXIN_MAP.get(k)
        if mixin is not None:
            mixin_classes.append(mixin)

    mixin_classes.append(GenericSubDevice)
    t = type(subdevice_id, tuple(mixin_classes), {})
    dev = t(hubdevice_uuid=hub_device.uuid, subdevice_id=subdevice_id, status=status, last_active_time=last_active_time, manager=hub_device._manager, **version_payload)
    return dev
