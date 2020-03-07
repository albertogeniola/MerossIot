from enum import Enum
from typing import Union

from meross_iot.cloud.abilities import HUB_MTS100_ALL, HUB_MTS100_TEMPERATURE, HUB_MTS100_MODE, HUB_TOGGLEX
from meross_iot.cloud.devices.subdevices.generic import GenericSubDevice
from meross_iot.cloud.timeouts import LONG_TIMEOUT
from meross_iot.logger import VALVES_LOGGER as l
from meross_iot.meross_event import DeviceSwitchStatusEvent, ThermostatTemperatureChange, ThermostatModeChange


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

    def __init__(self, cloud_client, subdevice_id, parent_hub, **kwords):
        super().__init__(cloud_client, subdevice_id, parent_hub, **kwords)

    def _handle_push_notification(self, namespace, payload, from_myself=False):
        # Let the Generic handler to handle the common events.
        handled = super()._handle_push_notification(namespace=namespace, payload=payload, from_myself=from_myself)
        if handled:
            return True

        # If the parent handler was unable to parse it, we do it here.
        evt = None
        if namespace == HUB_MTS100_ALL:
            self._raw_state.update(payload)
            return True

        elif namespace == HUB_TOGGLEX:
            togglex = self._raw_state.get('togglex')
            if togglex is None:
                togglex = {}
                self._raw_state['togglex'] = togglex
            togglex.update(payload)
            evt = DeviceSwitchStatusEvent(self, 0, self.onoff, from_myself)
            self.fire_event(evt)
            return True

        elif namespace == HUB_MTS100_MODE:
            mode = self._raw_state.get('mode')
            if mode is None:
                mode = {}
                self._raw_state['mode'] = mode

            mode.update(payload)
            evt = ThermostatModeChange(device=self, mode=self.mode, generated_by_myself=from_myself)
            self.fire_event(evt)
            return True

        elif namespace == HUB_MTS100_TEMPERATURE:
            temp = self._raw_state.get('temperature')
            if temp is None:
                temp = {}
                self._raw_state['temperature'] = temp

            temp.update(payload)
            evt = ThermostatTemperatureChange(device=self,
                                              temperature_state=self._raw_state.get('temperature'),
                                              generated_by_myself=from_myself)
            self.fire_event(evt)
            return True

        # TODO: handle TIME SYNC event?
        # elif namespace == HUB_TIME_SYNC:
        #    self._state.get('??').update(payload)

        else:
            l.warn("Unsupported/unhandled event: %s" % namespace)
            l.debug("Namespace: %s, Data: %s" % (namespace, payload))
            return False

    @property
    def _status_token(self):
        return HUB_MTS100_ALL

    @property
    def onoff(self):
        onoff = self._get_property('togglex', 'onoff')
        return onoff

    @property
    def heating(self):
        heating = self._get_property('temperature', 'heating')
        if heating is None:
            return None
        else:
            return heating == 1

    @property
    def room_temperature(self):
        temp = self._get_property('temperature', 'room')
        if temp is None:
            return None
        else:
            return temp / 10

    @property
    def target_temperature(self):
        """
        Returns the current target temperature
        :return:
        """
        # The API returns the temperature in decimals.
        # For this reason, we convert it to integers.
        temp = self._get_property('temperature', 'currentSet')
        if temp is None:
            return None
        else:
            return temp / 10

    def set_target_temperature(self,
                               target_temp: float = None,
                               timeout : float = LONG_TIMEOUT,
                               callback: callable = None):
        """
        Sets the target temperature of the thermostat
        :param target_temp: temperature to be set
        :param callback:
        :return:
        """
        # The API expects the target temperature in DECIMALS, so we need to multiply the user's input by 10
        value = target_temp * 10
        payload = {'temperature': [{'id': self.subdevice_id, 'custom': value}]}
        return self.execute_command(command='SET',
                                    namespace=HUB_MTS100_TEMPERATURE,
                                    payload=payload,
                                    timeout=timeout,
                                    callback=callback)

    def set_preset_temperature(self,
                               away: float = None,
                               comfort: float = None,
                               economy: float = None,
                               timeout: float = LONG_TIMEOUT,
                               callback: callable = None):
        """
        Configures the preset temperature values. The temperature values should be expressed in
        Celsius degrees.
        :param away: Target temperature for away preset
        :param comfort: Target temperature for comfort preset
        :param economy: Target temperature for economy preset
        :param callback:
        :return:
        """
        # The API expects the celsius degrees in DECIMALS, so we need to multiply the user's input by 10
        temperature_conf = {'id': self.subdevice_id}
        if away is not None:
            temperature_conf['away'] = away * 10
        if comfort is not None:
            temperature_conf['comfort'] = comfort * 10
        if economy is not None:
            temperature_conf['economy'] = economy * 10

        payload = {'temperature': [temperature_conf]}
        return self.execute_command(command='SET',
                                    namespace=HUB_MTS100_TEMPERATURE,
                                    payload=payload,
                                    timeout=timeout,
                                    callback=callback)

    @property
    def mode(self):
        state = self._get_property('mode', 'state')
        if state is None:
            return None
        else:
            # Parse the mode according to the current device type
            if self.type == 'mts100v3':
                return ThermostatV3Mode(state)
            elif self.type == 'mts100':
                return ThermostatMode(state)
            else:
                l.error("The current thermostat mode is not supported.")
                return None

    def set_mode(self,
                 mode: Union[ThermostatV3Mode, ThermostatMode, int],
                 timeout=LONG_TIMEOUT,
                 callback=None
                 ):
        """
        Sets the temperature mode for the thermostat
        :param mode:
        :return:
        """
        # Make sure we are passing correct values
        if self.type == 'mts100v3' and not isinstance(mode, ThermostatV3Mode):
            raise ValueError("This thermostat only supports ThermostatV3Mode modes")
        elif self.type == 'mts100' and not isinstance(mode, ThermostatMode):
            raise ValueError("This thermostat only supports ThermostatMode modes")
        elif isinstance(mode, int):
            l.warning("Setting a raw integer value as mode. This is not recommended. "
                      "Please use ThermostatMode or ThermostatV3Mode")
        self.execute_command('SET', HUB_MTS100_MODE, {'mode': [{'id': self.subdevice_id, 'state': mode.value}]},
                             timeout=timeout, callback=callback)

    def _togglex(self, onoff, channel=0, timeout=LONG_TIMEOUT, callback=None):
        payload = {'togglex': [{'channel': channel, 'id': self.subdevice_id, 'onoff': onoff}]}
        return self.execute_command('SET', HUB_TOGGLEX, payload, timeout=timeout, callback=callback)

    def turn_on(self, timeout=LONG_TIMEOUT, callback=None):
        return self._togglex(onoff=1, timeout=timeout, callback=callback)

    def turn_off(self, timeout=LONG_TIMEOUT, callback=None):
        return self._togglex(onoff=0, timeout=timeout, callback=callback)
