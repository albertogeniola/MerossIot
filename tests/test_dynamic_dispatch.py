import logging
from multiprocessing import Process

import socks
from aiohttp import web
from aiohttp.test_utils import AioHTTPTestCase, unittest_run_loop
from meross_iot import device_factory
from meross_iot.controller.device import BaseDevice, HubDevice, GenericSubDevice
from meross_iot.manager import MerossManager
from meross_iot.model.enums import OnlineStatus, Namespace
from tests import async_get_client
import os
from meross_iot.controller.mixins.consumption import ConsumptionXMixin, ConsumptionMixin
from meross_iot.controller.mixins.diffuser_light import DiffuserLightMixin
from meross_iot.controller.mixins.diffuser_spray import DiffuserSprayMixin
from meross_iot.controller.mixins.dnd import SystemDndMixin
from meross_iot.controller.mixins.electricity import ElectricityMixin
from meross_iot.controller.mixins.encryption import EncryptionSuiteMixin
from meross_iot.controller.mixins.garage import GarageOpenerMixin
from meross_iot.controller.mixins.hub import HubMts100Mixin, HubMixn, HubMs100Mixin
from meross_iot.controller.mixins.light import LightMixin
from meross_iot.controller.mixins.roller_shutter import RollerShutterTimerMixin
from meross_iot.controller.mixins.runtime import SystemRuntimeMixin
from meross_iot.controller.mixins.spray import SprayMixin
from meross_iot.controller.mixins.system import SystemAllMixin, SystemOnlineMixin
from meross_iot.controller.mixins.thermostat import ThermostatModeMixin, ThermostatModeBMixin
from meross_iot.controller.mixins.toggle import ToggleXMixin, ToggleMixin
from meross_iot.controller.subdevice import Mts100v3Valve, Ms100Sensor
from meross_iot.model.enums import Namespace
from meross_iot.model.exception import UnknownDeviceType
from meross_iot.model.http.device import HttpDeviceInfo
from meross_iot.model.http.subdevice import HttpSubdeviceInfo

# Note:you may have to add the parent directory to this test. 
# On *NIX, run: export PYTHONPATH=$PYTHONPATH:$(pwd) from the parent directory
# On windows, run: $env:PYTHONPATH = $pwd from the parent directory

_LOGGER = logging.getLogger(__name__)

if os.name == 'nt':
    import asyncio

    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
else:
    import asyncio
    
_ABILITY_MATRIX = {
    # Power plugs abilities
    Namespace.CONTROL_TOGGLEX.value: ToggleXMixin,
    Namespace.CONTROL_TOGGLE.value: ToggleMixin,
    Namespace.CONTROL_CONSUMPTIONX.value: ConsumptionXMixin,
    Namespace.CONTROL_CONSUMPTION.value: ConsumptionMixin,
    Namespace.CONTROL_ELECTRICITY.value: ElectricityMixin,

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
    Namespace.HUB_ONLINE.value: HubMixn,
    Namespace.HUB_TOGGLEX.value: HubMixn,

    Namespace.HUB_SENSOR_ALL.value: HubMs100Mixin,
    Namespace.HUB_SENSOR_ALERT.value: HubMs100Mixin,
    Namespace.HUB_SENSOR_TEMPHUM.value: HubMs100Mixin,

    Namespace.HUB_MTS100_ALL.value: HubMts100Mixin,
    Namespace.HUB_MTS100_MODE.value: HubMts100Mixin,
    Namespace.HUB_MTS100_TEMPERATURE.value: HubMts100Mixin,

    # DND
    Namespace.SYSTEM_DND_MODE.value: SystemDndMixin,

    # Thermostat
    Namespace.CONTROL_THERMOSTAT_MODE.value: ThermostatModeMixin,
    Namespace.CONTROL_THERMOSTAT_MODEB.value: ThermostatModeBMixin,

    # TODO: BIND, UNBIND, ONLINE, WIFI, ETC!
}

class TestDispatch():
    def test_ability_matrix_mapping(self):
        for ability, cls in _ABILITY_MATRIX.items():
            dynamicCls = device_factory._dynamic_filter(ability,"xxx")
            assert dynamicCls == cls
    
    def test_dynamic_mixin_creation(self):
        # Create dynamic mixin
        abilities = {'Appliance.Config.Key': {}, 'Appliance.Config.WifiList': {}, 'Appliance.Config.Wifi': {}, 'Appliance.Config.WifiX': {}, 'Appliance.Config.Trace': {}, 'Appliance.Config.Info': {}, 'Appliance.Config.OverTemp': {}, 
                 'Appliance.Config.CustomTimer': {}, 'Appliance.Digest.CustomTimer': {}, 'Appliance.System.All': {}, 'Appliance.System.Hardware': {}, 'Appliance.System.Firmware': {}, 'Appliance.System.Debug': {}, 
                 'Appliance.System.Online': {}, 'Appliance.System.Time': {}, 'Appliance.System.Clock': {}, 'Appliance.System.Ability': {}, 'Appliance.System.Runtime': {}, 'Appliance.System.Report': {}, 'Appliance.System.Position': {}, 
                 'Appliance.Control.Multiple': {'maxCmdNum': 3}, 'Appliance.Control.Bind': {}, 'Appliance.Control.Unbind': {}, 'Appliance.Control.Upgrade': {}, 'Appliance.Control.OverTemp': {}, 
                 'Appliance.Control.ToggleX': {}, 'Appliance.Control.Luminance': {}}
        mixin = device_factory._build_cached_type("test",abilities,BaseDevice,"test")

        for ability in abilities:
            try:
                abilityMatrixCls = _ABILITY_MATRIX[ability]
                # We could use isinstance, but the assert messages look nicer this way
                assert abilityMatrixCls in mixin.__bases__
            except KeyError:
                continue

