from enum import Enum

from meross_iot.cloud.abilities import HUB_MTS100_ALL, HUB_MTS100_TEMPERATURE, HUB_MTS100_MODE
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
    mode = None
    #heating = None
    open_window = None
    target_temperature = None
    room_temperature = None
    custom_temperature = None
    comfort_temperature = None
    economy_temperature = None
    max_temperature = None
    min_temperature = None

    type = 'Unknown'

    def __init__(self, subdevice_id, hub, **kwords):
        super().__init__(subdevice_id, hub, **kwords)
        if 'mts100v3' in kwords:
            self.type = 'mts100v3'
        elif 'mts100' in kwords:
            self.type = 'mts100'

    def update_all(self):
        payload = {'all': [{'id': self.id}]}
        res = self._hub.execute_command('GET', HUB_MTS100_ALL, payload)
        my_data = res.get('all')[0]
        self._update_all(my_data)

    def handle_push_event(self, subdevice_data, namespace):
        if namespace == HUB_MTS100_ALL:
            self._update_all(subdevice_data)
        elif namespace == HUB_MTS100_MODE:
            self._update_mode(subdevice_data)
        elif namespace == HUB_MTS100_TEMPERATURE:
            self._update_temperature(subdevice_data)
        else:
            # In any other case, invoke the generic subdevice handler
            super().handle_push_event(subdevice_data, namespace)

    def _update_mode(self, mode):
        mode_state = mode.get('state')
        if self.type == 'mts100':
            self.mode = ThermostatMode(mode_state)
        elif self.type == 'mts100v3':
            self.mode = ThermostatV3Mode(mode_state)

    def _update_temperature(self, temperature_data):
        if 'room' in temperature_data:
            self.room_temperature = temperature_data.get('room')
        if 'currentSet' in temperature_data:
            self.target_temperature = temperature_data.get('currentSet')
        if 'custom' in temperature_data:
            self.custom_temperature = temperature_data.get('custom')
        if 'comfort' in temperature_data:
            self.comfort_temperature = temperature_data.get('comfort')
        if 'economy' in temperature_data:
            self.economy_temperature = temperature_data.get('economy')
        if 'max' in temperature_data:
            self.max_temperature = temperature_data.get('max')
        if 'min' in temperature_data:
            self.min_temperature = temperature_data.get('min')
        if 'openWindow' in temperature_data:
            self.open_window = temperature_data.get('openWindow') == 1

    def _update_all(self, my_data):
        if 'online' in my_data and 'lastActiveTime' in my_data.get('online'):
            self.last_active_time = my_data.get('online').get('lastActiveTime')

        if 'online' in my_data and 'status' in my_data.get('online'):
            self.online = my_data.get('online').get('status') == 1

        if 'togglex' in my_data and 'onoff' in my_data.get('togglex'):
            self.onoff = my_data.get('togglex').get('onoff')

        if 'mode' in my_data:
            self._update_mode(my_data.get('mode'))

        if 'temperature' in my_data:
            temps = my_data.get('temperature')
            self._update_temperature(temps)

            # It's never TRUE: probably is driven by the app comparing the target with the room
            # self.heating = temps.get('heating') == 1

    def __str__(self):
        return "mode={}, room={}, target={}, open window={}".format(self.mode, self.room_temperature,
                                                                    self.target_temperature,
                                                                    self.open_window)
