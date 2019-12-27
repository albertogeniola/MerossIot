from enum import Enum

from meross_iot.cloud.abilities import HUB_MTS100_ALL, HUB_MTS100_TEMPERATURE, HUB_MTS100_MODE, HUB_TOGGLEX, \
    HUB_MTS100_ONLINE
from meross_iot.cloud.devices.subdevices.generic import GenericSubDevice
from meross_iot.logger import VALVES_LOGGER as l
from meross_iot.meross_event import DeviceSwitchStatusEvent, ThermostatTemperatureChange, ThermostatModeChange, \
    DeviceOnlineStatusEvent


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
        evt = None
        if namespace == HUB_MTS100_ALL:
            self._raw_state.update(payload)
            # onoff and online properties are handled by the parent class. So, when a thermostat-specific event
            # is received, we need to update the parent properties as well.
            self.onoff = self._raw_state.get('togglex').get('onoff')
            self.online = self._raw_state.get('online').get('status')
            self.last_active_time = self._raw_state.get('online').get('lastActiveTime')
            # We do not fire events on HUB_MTS100_ALL push notification.

        elif namespace == HUB_TOGGLEX:
            togglex = self._raw_state.get('togglex')
            if togglex is None:
                togglex = {}
                self._raw_state['togglex'] = togglex

            togglex.update(payload)
            self.onoff = self._raw_state.get('togglex').get('onoff')
            evt = DeviceSwitchStatusEvent(self, 0, self.onoff, from_myself)
        elif namespace == HUB_MTS100_MODE:
            mode = self._raw_state.get('mode')
            if mode is None:
                mode = {}
                self._raw_state['mode'] = mode

            mode.update(payload)
            evt = ThermostatModeChange(device=self, mode=self.mode, generated_by_myself=from_myself)

        elif namespace == HUB_MTS100_TEMPERATURE:
            temp = self._raw_state.get('temperature')
            if temp is None:
                temp = {}
                self._raw_state['temperature'] = temp

            temp.update(payload)
            evt = ThermostatTemperatureChange(device=self,
                                              temperature_state=self._raw_state.get('temperature'),
                                              generated_by_myself=from_myself)

        elif namespace == HUB_MTS100_ONLINE:  # TODO: check if this really exists
            online = self._raw_state.get('online')
            if online is None:
                online = {}
                self._raw_state['online'] = online

            online.update(payload)
            self.online = self._raw_state.get('online').get('status')
            self.last_active_time = self._raw_state.get('online').get('lastActiveTime')
            evt = DeviceOnlineStatusEvent(dev=self, current_status=payload)  # TODO: check the payload value and the expected event value

        # TODO: handle TIME SYNC event?
        # elif namespace == HUB_TIME_SYNC:
        #    self._state.get('??').update(payload)

        else:
            l.warn("Unsupported/unhandled event: %s" % namespace)

        # If any event has been prepared, fire it now.
        if evt is not None:
            self.fire_event(evt)

    @property
    def mode(self):
        state = self._raw_state.get('mode', {}).get('state')
        if state is None:
            return None

        # Parse the mode according to the current device type
        if self.type == 'mts100v3':
            return ThermostatV3Mode(state)
        elif self.type == 'mts100':
            return ThermostatMode(state)
        else:
            l.error("The current thermostat mode is not supported.")
            return None
