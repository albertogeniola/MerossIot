import logging
from typing import Optional, List, Dict

from meross_iot.controller.device import ChannelInfo
from meross_iot.model.enums import Namespace, ThermostatMode

_LOGGER = logging.getLogger(__name__)


_THERMOSTAT_MIN_SETTABLE_TEMP = 5.0
_THERMOSTAT_MAX_SETTABLE_TEMP = 35


class ThermostatState:
    _state: Dict
    def __init__(self, state: Dict = None):
        if state is not None:
            self._state = state

    def update(self, state: Dict):
        """
        Updates the internal state from the raw data dictionary passed as parameter
        :param state:
        :return:
        """
        self._state.update(state)

    @property
    def is_on(self) -> Optional[bool]:
        """Whether the device is on or not."""
        on = self._state.get('onoff')
        if on is None:
            return None
        return on == 1

    @property
    def mode(self) -> Optional[ThermostatMode]:
        """The current thermostat mode"""
        mode = self._state.get('mode')
        if mode is None:
            return None
        return ThermostatMode(mode)

    @property
    def warning(self) -> Optional[bool]:
        """The warning state of the thermostat"""
        warn = self._state.get('warning')
        if warn is None:
            return None
        return warn == 1

    @property
    def target_temperature_celsius(self) -> Optional[float]:
        """The target temperature of the thermostat"""
        temp = self._state.get('targetTemp')
        if temp is None:
            return None
        return float(temp)/10.0

    @property
    def min_temperature_celsius(self) -> Optional[float]:
        """The minimum settable temperature for the thermostat"""
        temp = self._state.get('min')
        if temp is None:
            return None
        return float(temp)/10.0

    @property
    def max_temperature_celsius(self) -> Optional[float]:
        """The maximum settable temperature for the thermostat"""
        temp = self._state.get('max')
        if temp is None:
            return None
        return float(temp)/10.0

    @property
    def current_temperature_celsius(self) -> Optional[float]:
        """The current ambient temperature"""
        temp = self._state.get('currentTemp')
        if temp is None:
            return None
        return float(temp)/10.0

    @property
    def heat_temperature_celsius(self) -> Optional[float]:
        """The target temperature when HEAT mode is enabled"""
        temp = self._state.get('heatTemp')
        if temp is None:
            return None
        return float(temp)/10.0

    @property
    def cool_temperature_celsius(self) -> Optional[float]:
        """The target temperature when COOL mode is enabled"""
        temp = self._state.get('coolTemp')
        if temp is None:
            return None
        return float(temp)/10.0

    @property
    def eco_temperature_celsius(self) -> Optional[float]:
        """The target temperature when ECO mode is enabled"""
        temp = self._state.get('ecoTemp')
        if temp is None:
            return None
        return float(temp)/10.0

    @property
    def manual_temperature_celsius(self) -> Optional[float]:
        """The target temperature when AUTO mode is enabled"""
        temp = self._state.get('manualTemp')
        if temp is None:
            return None
        return float(temp)/10.0


class ThermostatModeMixin:
    _execute_command: callable
    check_full_update_done: callable
    _thermostat_state_by_channel: Dict[int, ThermostatState]

    def __init__(self, device_uuid: str,
                 manager,
                 **kwargs):
        super().__init__(device_uuid=device_uuid, manager=manager, **kwargs)
        self._thermostat_state_by_channel = {}

    def _update_mode(self, mode_data: Dict):
        # The MTS200 thermostat does bring a object for every sensor/channel it handles.
        for c in mode_data:
            channel_index = c['channel']
            state = self._thermostat_state_by_channel.get(channel_index)
            if state is None:
                state = ThermostatState(c)
                self._thermostat_state_by_channel[channel_index] = state
            else:
                state.update(c)

    async def async_handle_push_notification(self, namespace: Namespace, data: dict) -> bool:
        locally_handled = False

        if namespace == Namespace.CONTROL_THERMOSTAT_MODE:
            _LOGGER.debug(f"{self.__class__.__name__} handling push notification for namespace "
                          f"{namespace}")
            mode_data = data.get('mode')
            if mode_data is None:
                _LOGGER.error(f"{self.__class__.__name__} could not find 'mode' attribute in push notification data: "
                              f"{data}")
                locally_handled = False
            else:
                self._update_mode(mode_data)
                locally_handled = True

        # Always call the parent handler when done with local specific logic. This gives the opportunity to all
        # ancestors to catch all events.
        parent_handled = await super().async_handle_push_notification(namespace=namespace, data=data)
        return locally_handled or parent_handled

    async def async_handle_update(self, namespace: Namespace, data: dict) -> bool:
        _LOGGER.debug(f"Handling {self.__class__.__name__} mixin data update.")
        locally_handled = False
        if namespace == Namespace.SYSTEM_ALL:
            thermostat_data = data.get('all', {}).get('digest', {}).get('thermostat', {})
            mode_data = thermostat_data.get('mode')
            if mode_data is not None:
                self._update_mode(mode_data)
            locally_handled = True

        super_handled = await super().async_handle_update(namespace=namespace, data=data)
        return super_handled or locally_handled

    def get_thermostat_state(self, channel: int = 0, *args, **kwargs) -> Optional[ThermostatState]:
        """
        Returns the current thermostat state
        :param channel:
        :param args:
        :param kwargs:
        :return:
        """
        self.check_full_update_done()
        state = self._thermostat_state_by_channel.get(channel)
        return state

    def _align_temp(self, temperature:float, channel: int = 0) -> float:
        """
            Given an input temperature for a specific channel, checks if the temperature is within the ranges
            of acceptable values and rounds it to the nearest 0.5 value. It also applies the 10x multiplication
            as Meross devices requires decimal-degrees
        """
        # Retrieve the min/max settable values from the state.
        # If this is not available, assume some defaults
        channel_state = self._thermostat_state_by_channel.get(channel)
        min_settable_temp = _THERMOSTAT_MIN_SETTABLE_TEMP
        max_settable_temp = _THERMOSTAT_MIN_SETTABLE_TEMP
        if channel_state is not None:
            min_settable_temp = channel_state.min_temperature_celsius
            max_settable_temp = channel_state.max_temperature_celsius

        if temperature < min_settable_temp or temperature > max_settable_temp:
            raise ValueError("The provided temperature value is invalid or out of range for this device.")

        # Round temp value to 0.5
        quotient = temperature/0.5
        quotient = round(quotient)
        final_temp = quotient*5
        return final_temp

    async def async_set_thermostat_config(self,
                                    channel: int = 0,
                                    mode: Optional[ThermostatMode] = None,
                                    manual_temperature_celsius: Optional[float] = None,
                                    heat_temperature_celsius: Optional[float] = None,
                                    cool_temperature_celsius: Optional[float] = None,
                                    eco_temperature_celsius: Optional[float] = None,
                                    on_not_off: Optional[bool] = None,
                                    timeout: Optional[float] = None,
                                    *args,
                                    **kwargs) -> None:
        channel_conf = {
            'channel': channel
        }
        payload = {'mode': [channel_conf]}

        # Arg check
        if mode is not None:
            channel_conf['mode'] = mode.value
        if manual_temperature_celsius is not None:
            channel_conf['manualTemp'] = self._align_temp(manual_temperature_celsius, channel=channel)
        if heat_temperature_celsius is not None:
            channel_conf['heatTemp'] = self._align_temp(heat_temperature_celsius, channel=channel)
        if cool_temperature_celsius is not None:
            channel_conf['coolTemp'] = self._align_temp(cool_temperature_celsius, channel=channel)
        if eco_temperature_celsius is not None:
            channel_conf['ecoTemp'] = self._align_temp(eco_temperature_celsius, channel=channel)
        if on_not_off is not None:
            channel_conf['onoff'] = 1 if on_not_off else 0

        # This api call will return the updated state of the device. We use it to update the internal state right away.
        result = await self._execute_command(method="SET",
                              namespace=Namespace.CONTROL_THERMOSTAT_MODE,
                                         payload=payload,
                                         timeout=timeout)
        mode_data = result.get('mode')
        self._update_mode(mode_data)
