import logging
from typing import List

from meross_iot.cloud.device import BaseMerossDevice
from meross_iot.cloud.mixins.toggle import ToggleXMixin
from meross_iot.model.enums import Namespace, get_or_parse_namespace
from meross_iot.model.http.device import HttpDeviceInfo


_LOGGER = logging.getLogger(__name__)


_ABILITY_MATRIX = {
    Namespace.TOGGLEX.value: ToggleXMixin
    #Namespace.SYSTEM_ALL: pass
    # TODO:
}


def add_mixins(base_component: BaseMerossDevice, classes: List[type], class_name: str) -> BaseMerossDevice:
    if len(classes) < 1:
        return base_component

    classes = classes.copy()
    classes.append(base_component.__class__)
    base_component.__class__ = type(class_name, tuple(classes), {})
    return base_component


def build_meross_device(http_device_info: HttpDeviceInfo, device_abilities: dict, manager) -> BaseMerossDevice:
    _LOGGER.debug(f"Building managed device for {http_device_info.dev_name} ({http_device_info.uuid}). "
                  f"Reported abilities: {device_abilities}")

    # TODO: Pick the base class between BaseWifiDevice/HubWifiDevice/etc...
    base_component = BaseMerossDevice(device_uuid=http_device_info.uuid, manager=manager, **http_device_info.to_dict())
    mixin_classes = []

    # Add abilities
    for key, val in device_abilities.items():
        cls = _ABILITY_MATRIX.get(key)
        if cls is not None:
            mixin_classes.append(cls)

    component = add_mixins(base_component=base_component, classes=mixin_classes, class_name=http_device_info.device_type.upper())
    return component
