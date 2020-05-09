import logging
from enum import Enum
from typing import Union


_LOGGER = logging.getLogger(__name__)


class OnlineStatus(Enum):
    ONLINE = 1
    OFFLINE = 2


class LightMode(Enum):
    MODE_LUMINANCE = 4
    MODE_TEMPERATURE = 2
    MODE_RGB = 1
    MODE_RGB_LUMINANCE = 5
    MODE_TEMPERATURE_LUMINANCE = 6


class Namespace(Enum):
    # Common abilities
    SYSTEM_ALL = 'Appliance.System.All'
    ABILITY = 'Appliance.System.Ability'
    ONLINE = 'Appliance.System.Online'
    REPORT = 'Appliance.System.Report'
    DEBUG = 'Appliance.System.Debug'

    BIND = 'Appliance.Control.Bind'
    UNBIND = 'Appliance.Control.Unbind'
    TRIGGER = 'Appliance.Control.Trigger'
    TRIGGERX = 'Appliance.Control.TriggerX'
    WIFI_LIST = 'Appliance.Config.WifiList'
    TRACE = 'Appliance.Config.Trace'

    # Power plug/bulbs abilities
    TOGGLE = 'Appliance.Control.Toggle'
    TOGGLEX = 'Appliance.Control.ToggleX'
    ELECTRICITY = 'Appliance.Control.Electricity'
    CONSUMPTIONX = 'Appliance.Control.ConsumptionX'

    # Bulbs-only abilities
    LIGHT = 'Appliance.Control.Light'

    # Garage opener abilities
    GARAGE_DOOR_STATE = 'Appliance.GarageDoor.State'

    # Humidifier
    SPRAY = 'Appliance.Control.Spray'

    # Hub
    HUB_TOGGLEX = 'Appliance.Hub.ToggleX'
    HUB_ONLINE = 'Appliance.Hub.Online'
    HUB_MTS100_TEMPERATURE = 'Appliance.Hub.Mts100.Temperature'
    HUB_MTS100_MODE = 'Appliance.Hub.Mts100.Mode'
    HUB_MTS100_ALL = 'Appliance.Hub.Mts100.All'
    HUB_MS100_ALL = 'Appliance.Hub.Sensor.All'
    HUB_MS100_TEMPHUM = 'Appliance.Hub.Sensor.TempHum'
    HUB_MS100_ALERT = 'Appliance.Hub.Sensor.Alert'
    HUB_EXCEPTION = 'Appliance.Hub.Exception'
    HUB_BATTERY = 'Appliance.Hub.Battery'


def get_or_parse_namespace(namespace: Union[Namespace, str]):
    if isinstance(namespace, str):
        try:
            parsed_namespace = Namespace(namespace)
            return parsed_namespace
        except ValueError:
            _LOGGER.error(f"Namespace {namespace} is not currently handled/recognized.")
            raise
    elif isinstance(namespace, Namespace):
        return namespace
    else:
        raise ValueError("Unknown invalid namespace type. Only str/Namespace types are allowed here.")