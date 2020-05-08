import logging
from typing import List

from meross_iot.cloud.device import BaseMerossDevice
from meross_iot.cloud.mixins.toggle import ToggleXMixin, ToggleMixin
from meross_iot.model.enums import Namespace, get_or_parse_namespace
from meross_iot.model.http.device import HttpDeviceInfo


_LOGGER = logging.getLogger(__name__)


# TODO: implement logic to "selectively discard overlapping capabilities"
_ABILITY_MATRIX = {
    Namespace.TOGGLEX.value: ToggleXMixin,
    Namespace.TOGGLE.value: ToggleMixin
    #Namespace.SYSTEM_ALL: pass
    # TODO:
}


def build_meross_device(http_device_info: HttpDeviceInfo, device_abilities: dict, manager) -> BaseMerossDevice:
    _LOGGER.debug(f"Building managed device for {http_device_info.dev_name} ({http_device_info.uuid}). "
                  f"Reported abilities: {device_abilities}")

    # Build a specific type at runtime by mixing mixins on-demand
    mixin_classes = []

    # Add mixins by abilities
    for key, val in device_abilities.items():
        cls = _ABILITY_MATRIX.get(key)
        if cls is not None:
            mixin_classes.append(cls)

    # TODO: register every type so that we don't create a specific type per instance.

    # Add the base class
    mixin_classes.append(BaseMerossDevice)
    m = type(http_device_info.device_type, tuple(mixin_classes), {})
    component = m(device_uuid=http_device_info.uuid, manager=manager, **http_device_info.to_dict())
    return component
