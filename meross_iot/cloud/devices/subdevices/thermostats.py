from enum import Enum
from meross_iot.cloud.devices.subdevices.generic import GenericSubDevice
from meross_iot.logger import VALVES_LOGGER as l


class ThermostatMode(Enum):
    COMFORT = 1
    CUSTOM = 0
    ECONOMY = 2
    SCHEDULE = 3


class ThermostatV3Mode(Enum):
    AUTO = 3
    COOL = 2
    CUSTOM = 0
    ECONOMY = 4
    HEAT = 1


class ValveSubDevice(GenericSubDevice):
    _MINIMUM_TEMPERATURE = 50
    _MAXIMUM_TEMPERATURE = 350
    mode = None
    target_temperature = None

    def __init__(self, subdevice_id, hub, **kwords):
        super().__init__(subdevice_id, hub, **kwords)

    def update_state(self, subdevice_data):
        super().update_state(subdevice_data)

        # Mode
        if 'mts100v3' in subdevice_data:
            self.mode = ThermostatV3Mode(subdevice_data.get('mts100v3').get('mode'))
        elif 'mts100v3' in subdevice_data:
            self.mode = ThermostatMode(subdevice_data.get('mts100').get('mode'))

        # Target temperature
        current_set = subdevice_data.get('currentSet')
        if current_set is not None:
            self.target_temperature = current_set

    def __str__(self):
        return "mode={}, target_temperature={}".format(self.mode, self.target_temperature)
