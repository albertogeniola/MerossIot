import logging
from typing import Optional
import inspect
import sys
import pkgutil
from importlib import import_module

from meross_iot.controller.mixins import *
from meross_iot.controller.mixins.utilities import *
from meross_iot.controller.device import BaseDevice, HubDevice, GenericSubDevice
from meross_iot.controller.subdevice import Mts100v3Valve, Ms100Sensor
from meross_iot.model.enums import Namespace
from meross_iot.model.exception import UnknownDeviceType
from meross_iot.model.http.device import HttpDeviceInfo
from meross_iot.model.http.subdevice import HttpSubdeviceInfo

_LOGGER = logging.getLogger(__name__)

_KNOWN_DEV_TYPES_CLASSES = {
    "mts100v3": Mts100v3Valve,
    "ms100": Ms100Sensor,
    "ms100f": Ms100Sensor
}


_SUBDEVICE_MAPPING = {
    "mts100v3": Mts100v3Valve,
    "ms100": Ms100Sensor,
    "ms100f": Ms100Sensor
}

_dynamic_types = {}
dynamic_plugins = {}


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

def _load_mixins(packageName = "meross_iot.controller.mixins"):
    # Only do this once.
    if len(dynamic_plugins) > 0:
        return
    
    for moduleName in pkgutil.iter_modules(sys.modules[packageName].__path__):       
        module = import_module(f'{packageName}.{moduleName.name}')

        for name, obj in inspect.getmembers(module):
            if inspect.isclass(obj):
                # Ignore things in the utilities namespace
                if obj.__module__ == "meross_iot.controller.mixins.utilities":
                    continue

                # Only load dynamically-filterable mixins
                if issubclass(obj,DynamicFilteringMixin):
                    dynamic_plugins[name] = obj

def _add_classes_for_ability(device_ability : str,device_type : str, mixin_classes):
     # Load dynamic modules - if required.
    _load_mixins()
    loadedClasses = False
    for name,clazz in dynamic_plugins.items():
        _LOGGER.debug(f'Testing mixin: {name} for {device_type}')
        # Try filtering
        if clazz.filter(device_ability,device_type) == True:
            shouldAdd = True

            # Some devices will expose the same ability like Tooggle and ToogleX. This loop confirms that we prefer the X version.
            for existingClass in mixin_classes:
                if clazz == existingClass:
                    # We don't want to add the same class multiple times. In the case we do (due to an overly-permissive filter)
                    # Drop out of this loop and carry on to the next plugin
                    shouldAdd = False 
                    # Lie and say we were successful on the return status
                    loadedClasses = True 
                else:
                    # We need to first test if a we already have a subclassed mixin cached. This means the X version has already been found.
                    if issubclass(existingClass,clazz):
                        shouldAdd = False
                        continue
                    # We prefer the X version by testing if we have any parent classes of class returned by _dynamic_filter
                    if issubclass(clazz,existingClass):
                        # Erase old class
                        mixin_classes.remove(existingClass)
                        shouldAdd = True
                        break
            if shouldAdd: # Just add
                mixin_classes.append(clazz)
                _LOGGER.debug(f'Loaded mixin: {name} for {device_type}')

                loadedClasses = True

    return loadedClasses

    """ 
    def _add_mixin_class(clazz, mixin_classes):
    shouldAdd = True

    # Some devices will expose the same ability like Tooggle and ToogleX. This confirms that we prefer the X version.
    for existingClass in mixin_classes:
            # We need to first test if a we already have a subclassed mixin cached. This means the X version has already been found.
            if issubclass(existingClass,clazz):
                shouldAdd = False
                continue
            # We prefer the X version by testing if we have any parent classes of class returned by _dynamic_filter
            if issubclass(clazz,existingClass):
                # Erase old class
                mixin_classes.remove(existingClass)
                shouldAdd = True
                break
    if shouldAdd: # Just add
        mixin_classes.add(clazz)
        loadedClasses = True

    return shouldAdd
    """
    

def _build_cached_type(type_string: str, device_abilities: dict, base_class: type,device_type : str) -> type:
    """
    Builds a python type (class) dynamically by looking at the device abilities. In this way, we are able to
    "plugin" feature/mixins even for unknown new devices, given that they report abilities we already implemented.
    :param type_string:
    :param device_abilities:
    :return:
    """
    # Build a specific type at runtime by mixing plugins on-demand
    mixin_classes = list()
    # Add plugins via filtering
    _load_mixins()
    # We run through each plugin and try filtering on it until it matches. This allows us to prevent scanning to
    # check if we've already loaded a plugin
    for device_ability in device_abilities:
        _add_classes_for_ability(device_ability,device_type,mixin_classes)

    # We must be careful when ordering the mixin and leaving the BaseMerossDevice as last class.
    # Messing up with that will cause MRO to not resolve inheritance correctly.
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
        # of 'Appliance.Hub.SubdeviceList': if exposed, we assume the device is a fully featured hub.
        discriminating_abilities = [Namespace.HUB_SUBDEVICELIST.value]
        base_class = BaseDevice
        if any (da in device_abilities for da in discriminating_abilities):
            _LOGGER.warning(f"Device {http_device_info.dev_name} ({http_device_info.device_type}, "
                            f"uuid {http_device_info.uuid}) reported one ability of {discriminating_abilities}. "
                            f"Assuming this is a full-featured HUB.")
            base_class = HubDevice

        cached_type = _build_cached_type(type_string=device_type_name,
                                         device_abilities=device_abilities,
                                         base_class=base_class,
                                         device_type = http_device_info.device_type)
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
