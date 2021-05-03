import logging
from datetime import datetime
from typing import Optional, Iterable

from meross_iot.controller.device import GenericSubDevice
from meross_iot.model.enums import Namespace, OnlineStatus, ThermostatV3Mode

_LOGGER = logging.getLogger(__name__)


class Ms100Sensor(GenericSubDevice):
    """
    This class maps the functionality offered by the MS100 sensor device.
    The MS100 offers temperature and humidity sensing.
    Moreover, this device is capable of triggering settable alerts.
    """
    _UPDATE_ALL_NAMESPACE = Namespace.HUB_SENSOR_ALL

    def __init__(self, hubdevice_uuid: str, subdevice_id: str, manager, **kwargs):
        super().__init__(hubdevice_uuid, subdevice_id, manager, **kwargs)
        self.__temperature = {}
        self.__humidity = {}
        self.__samples = []

    async def _execute_command(self,
                               method: str,
                               namespace: Namespace,
                               payload: dict,
                               timeout: float = 5,
                               skip_rate_limits: bool = False,
                               drop_on_overquota: bool = True) -> dict:
        raise NotImplementedError("This method should never be called directly for subdevices.")

    async def async_handle_push_notification(self, namespace: Namespace, data: dict) -> bool:
        locally_handled = False
        if namespace == Namespace.HUB_ONLINE:
            update_element = self._prepare_push_notification_data(data=data, filter_accessor='online')
            self._online = OnlineStatus(update_element.get('status', -1))
            locally_handled = True
        elif namespace == Namespace.HUB_SENSOR_ALL:
            self._online = OnlineStatus(data.get('online', {}).get('status', -1))
            self.__temperature.update(data.get('temperature', {}))
            self.__humidity.update(data.get('humidity', {}))
            locally_handled = True
        elif namespace == Namespace.HUB_SENSOR_TEMPHUM:
            latest_temperature = data.get('latestTemperature')
            latest_humidity = data.get('latestHumidity')
            synced_time = data.get('syncedTime')
            samples = data.get('sample')
            if synced_time is not None and (self.last_sampled_time is None or
                                             synced_time > self.last_sampled_time.timestamp()):
                self.__temperature['latestSampleTime'] = synced_time
                self.__temperature['latest'] = latest_temperature
                self.__humidity['latestSampleTime'] = synced_time
                self.__humidity['latest'] = latest_humidity

            self.__samples.clear()
            for sample in samples:
                temp, hum, from_ts, to_ts, unknown = sample
                self.__samples.append({
                    'from_ts': from_ts,
                    'to_ts': to_ts,
                    'temperature': float(temp)/10,
                    'humidity': float(hum)/10
                })

            else:
                _LOGGER.debug("Skipping temperature update as synched time is None or old compared to the latest data")
            locally_handled = True
        elif namespace == Namespace.HUB_SENSOR_ALERT:
            locally_handled = False
            # TODO: not yet implemented

        # Always call the parent handler when done with local specific logic. This gives the opportunity to all
        # ancestors to catch all events.
        parent_handled = await super().async_handle_push_notification(namespace=namespace, data=data)
        return locally_handled or parent_handled

    @property
    def last_sampled_temperature(self) -> Optional[float]:
        """
        Returns the latest sampled temperature in Celsius degrees.
        If you want to refresh this data, call `async_update` to force a full
        data refresh.

        :return: The latest sampled temperature, if available, in Celsius degree
        """
        temp = self.__temperature.get('latest')
        if temp is None:
            return None
        return float(temp) / 10.0

    @property
    def last_sampled_humidity(self) -> Optional[float]:
        """
        Exposes the latest sampled humidity, in %.
        If you want to refresh this data, call `async_update` to force a full
        data refresh.

        :return: The latest sampled humidity grade in %, if available
        """
        humidity = self.__humidity.get('latest')
        if humidity is None:
            return None
        return float(humidity) / 10.0

    @property
    def last_sampled_time(self) -> Optional[datetime]:
        """
        UTC datetime when the latest update has been sampled by the sensor

        :return: latest sampling time in UTC, if available
        """
        timestamp = self.__temperature.get('latestSampleTime')
        if timestamp is None:
            return None

        return datetime.utcfromtimestamp(timestamp)

    @property
    def min_supported_temperature(self) -> Optional[float]:
        """
        Maximum supported temperature that this device can report

        :return: float value, maximum supported temperature, if available
        """
        return self.__temperature.get('min')

    @property
    def max_supported_temperature(self) -> Optional[float]:
        """
        Minimum supported temperature that this device can report
        """
        return self.__temperature.get('max')


class Mts100v3Valve(GenericSubDevice):
    _UPDATE_ALL_NAMESPACE = Namespace.HUB_MTS100_ALL

    def __init__(self, hubdevice_uuid: str, subdevice_id: str, manager, **kwargs):
        super().__init__(hubdevice_uuid, subdevice_id, manager, **kwargs)
        self.__togglex = {}
        self.__timeSync = None
        self.__mode = {}
        self.__temperature = {}
        self._schedule_b_mode = None
        self._last_active_time = None
        self.__adjust = {}

    async def _execute_command(self,
                               method: str,
                               namespace: Namespace,
                               payload: dict,
                               timeout: float = 5,
                               skip_rate_limits: bool = False,
                               drop_on_overquota: bool = True) -> dict:
        raise NotImplementedError("This method should never be called directly for subdevices.")

    async def async_handle_push_notification(self, namespace: Namespace, data: dict) -> bool:
        locally_handled = False
        if namespace == Namespace.HUB_ONLINE:
            update_element = self._prepare_push_notification_data(data=data, filter_accessor='online')
            self._online = OnlineStatus(update_element.get('status', -1))
            locally_handled = True
        elif namespace == Namespace.HUB_MTS100_ALL:
            self._schedule_b_mode = data.get('scheduleBMode')
            self._online = OnlineStatus(data.get('online', {}).get('status', -1))
            self._last_active_time = data.get('online', {}).get('lastActiveTime')
            self.__togglex.update(data.get('togglex', {}))
            self.__timeSync = data.get('timeSync', {})
            self.__mode.update(data.get('mode', {}))
            self.__temperature.update(data.get('temperature', {}))
            self.__temperature['latestSampleTime'] = datetime.utcnow().timestamp()
            self.__adjust.update(data.get('temperature', {}))
            self.__adjust['latestSampleTime'] = datetime.utcnow().timestamp()
            locally_handled = True
        elif namespace == Namespace.HUB_TOGGLEX:
            update_element = self._prepare_push_notification_data(data=data)
            self.__togglex.update(update_element)
            locally_handled = True
        elif namespace == Namespace.HUB_MTS100_MODE:
            update_element = self._prepare_push_notification_data(data=data)
            self.__mode.update(update_element)
            locally_handled = True
        elif namespace == Namespace.HUB_MTS100_TEMPERATURE:
            update_element = self._prepare_push_notification_data(data=data)
            self.__temperature.update(update_element)
            self.__temperature['latestSampleTime'] = datetime.utcnow().timestamp()
            locally_handled = True

        # Always call the parent handler when done with local specific logic. This gives the opportunity to all
        # ancestors to catch all events.
        parent_handled = await super().async_handle_push_notification(namespace=namespace, data=data)
        return locally_handled or parent_handled

    def is_on(self) -> Optional[bool]:
        return self.__togglex.get('onoff') == 1

    async def async_turn_off(self, skip_rate_limits: bool = False, drop_on_overquota: bool = True, *args, **kwargs):
        await self._hub._execute_command(method="SET",
                                         namespace=Namespace.HUB_TOGGLEX,
                                         payload={'togglex': [{"id": self.subdevice_id,"onoff": 0, "channel": 0}]},
                                         skip_rate_limits=skip_rate_limits,
                                         drop_on_overquota=drop_on_overquota)
        # Assume the command was ok, so immediately update the internal state
        self.__togglex['onoff'] = 0

    async def async_turn_on(self, skip_rate_limits: bool = False, drop_on_overquota: bool = True, *args, **kwargs):
        await self._hub._execute_command(method="SET",
                                         namespace=Namespace.HUB_TOGGLEX,
                                         payload={'togglex': [{"id": self.subdevice_id, "onoff": 1, "channel": 0}]},
                                         skip_rate_limits=skip_rate_limits,
                                         drop_on_overquota=drop_on_overquota)
        # Assume the command was ok, so immediately update the internal state
        self.__togglex['onoff'] = 1

    async def async_toggle(self, *args, **kwargs):
        if self.is_on():
            await self.async_turn_off()
        else:
            await self.async_turn_on()

    @property
    def last_sampled_temperature(self) -> Optional[float]:
        """
        Current room temperature in Celsius degrees.

        :return: float number
        """
        temp = self.__temperature.get('room')
        if temp is not None:
            return float(temp) / 10.0
        else:
            return None

    async def async_get_temperature(self, skip_rate_limits: bool = False, drop_on_overquota: bool = True, *args, **kwargs) -> Optional[float]:
        """
        Polls the device in order to retrieve the latest temperature info.
        You should not use this method so ofter: instead, rely on `last_sampled_temperature` when a cached
        value is ok.

        :return:
        """
        res = await self._hub._execute_command(method="GET",
                                               namespace=Namespace.HUB_MTS100_TEMPERATURE,
                                               payload={'temperature': [{"id": self.subdevice_id}]},
                                               skip_rate_limits=skip_rate_limits,
                                               drop_on_overquota=drop_on_overquota)
        if res is None:
            return None

        for d in res.get('temperature'):
            if d.get('id') == self.subdevice_id:
                del d['id']
                self.__temperature.update(d)
                self.__temperature['latestSampleTime'] = datetime.utcnow().timestamp()
                break

        return self.last_sampled_temperature

    @property
    def last_sampled_time(self) -> Optional[datetime]:
        """
        UTC datetime when the latest update has been sampled by the sensor

        :return: latest sampling time in UTC, if available
        """
        timestamp = self.__temperature.get('latestSampleTime')
        if timestamp is None:
            return None

        return datetime.fromtimestamp(timestamp)

    @property
    def mode(self) -> Optional[ThermostatV3Mode]:
        m = self.__mode.get('state')
        if m is not None:
            return ThermostatV3Mode(m)

    async def async_set_mode(self, mode: ThermostatV3Mode, skip_rate_limits: bool = False, drop_on_overquota: bool = True, *args, **kwargs) -> None:
        payload = {'mode': [{'id': self.subdevice_id, 'state': mode.value}]}
        await self._hub._execute_command(method='SET',
                                         namespace=Namespace.HUB_MTS100_MODE,
                                         payload=payload,
                                         skip_rate_limits=skip_rate_limits,
                                         drop_on_overquota=drop_on_overquota)
        self.__mode['state'] = mode.value

    @property
    def target_temperature(self) -> Optional[float]:
        temp = self.__temperature.get('currentSet')
        if temp is not None:
            return float(temp) / 10.0
        else:
            return None

    @property
    def min_supported_temperature(self) -> Optional[float]:
        temp = self.__temperature.get('min')
        if temp is not None:
            return float(temp) / 10.0
        else:
            return None

    @property
    def max_supported_temperature(self) -> Optional[float]:
        temp = self.__temperature.get('max')
        if temp is not None:
            return float(temp) / 10.0
        else:
            return None

    @property
    def is_heating(self) -> Optional[bool]:
        return self.__temperature.get('heating') == 1

    @property
    def is_window_open(self) -> Optional[bool]:
        return self.__temperature.get('openWindow') == 1

    def get_preset_temperature(self, preset: str) -> Optional[float]:
        """
        Returns the current set temperature for the given preset.

        :param preset:

        :return: float temperature value
        """
        if preset not in self.get_supported_presets():
            _LOGGER.error(f"Preset {preset} is not supported by this device.")
        val = self.__temperature.get(preset)
        if val is None:
            return None
        return float(val) / 10.0

    @staticmethod
    def get_supported_presets() -> Iterable[str]:
        """
        Returns the supported presets of this device.

        :return: an iterable of strings
        """
        return 'custom', 'comfort', 'economy', 'away'

    async def async_set_preset_temperature(self, preset: str, temperature: float, skip_rate_limits: bool = False, drop_on_overquota: bool = True, *args, **kwargs) -> None:
        """
        Sets the preset temperature configuration.

        :param preset: string preset, as reported by `get_supported_presets()`
        :param temperature: temperature to be set for the given preset

        :return: None
        """
        if preset not in self.get_supported_presets():
            raise ValueError(f"Preset {preset} is not supported by this device. "
                             f"Valid presets are: {self.get_supported_presets()}")
        target_temp = temperature * 10
        await self._hub._execute_command(method="SET",
                                         namespace=Namespace.HUB_MTS100_TEMPERATURE,
                                         payload={'temperature': [{'id': self.subdevice_id,preset: target_temp}]},
                                         skip_rate_limits=skip_rate_limits,
                                         drop_on_overquota=drop_on_overquota)

        # Update local state
        self.__temperature[preset] = target_temp

    async def async_set_target_temperature(self, temperature: float, skip_rate_limits: bool = False, drop_on_overquota: bool = True, *args, **kwargs) -> None:
        # The API expects the target temperature in DECIMALS, so we need to multiply the user's input by 10
        target_temp = temperature * 10
        payload = {'temperature': [{'id': self.subdevice_id, 'custom': target_temp}]}
        await self._hub._execute_command(method='SET',
                                         namespace=Namespace.HUB_MTS100_TEMPERATURE,
                                         payload=payload,
                                         skip_rate_limits=skip_rate_limits,
                                         drop_on_overquota=drop_on_overquota)
        # Update local state
        self.__temperature['currentSet'] = target_temp

    async def async_get_adjust(self, *args, **kwargs) -> Optional[float]:
        """
        :return:
        """
        res = await self._hub._execute_command("GET", Namespace.HUB_MTS100_ADJUST, {'adjust': [{"id": self.subdevice_id}]})
        if res is None:
            return None

        for d in res.get('adjust'):
            if d.get('id') == self.subdevice_id:
                del d['id']
                self.__adjust.update(d)
                self.__adjust['latestSampleTime'] = datetime.utcnow().timestamp()
                break

        return self.adjust

    @property
    def adjust(self) -> Optional[float]:
        """
        Returns the adjust temperature value for the sensor if available

        :return:
        """
        adjust = self.__adjust.get('temperature')
        if adjust is None:
            return None

        return float(self.__adjust.get('temperature')) / 100.0


    async def async_set_adjust(self, temperature: float) -> None:
        # The API expects the adjust temperature in HUNDREDS (not consistent with the temperature set), so we need to multiply the user's input by 100
        # N.B. the App enforces on the frontend a limit on the adjustment (+/- 5 C°), tests show there is no limit on the API
        adjust_temp = temperature * 100
        payload = {'adjust': [{'id': self.subdevice_id, 'temperature': adjust_temp}]}
        await self._hub._execute_command(method='SET',
                                          namespace=Namespace.HUB_MTS100_ADJUST,
                                          payload=payload)
        # Update local state
        self.__adjust.update({'temperature': adjust_temp})
        self.__adjust['latestSampleTime'] = datetime.utcnow().timestamp()
