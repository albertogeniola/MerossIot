import logging
from datetime import datetime
from typing import Optional, Iterable, Dict, List

from meross_iot.controller.device import GenericSubDevice
from meross_iot.model.enums import Namespace, OnlineStatus, ThermostatV3Mode

_LOGGER = logging.getLogger(__name__)


class Mts100Mixin(GenericSubDevice):

    def __init__(self, hubdevice_uuid:str, subdevice_id:str, status:int, last_active_time:int, manager):
        super().__init__(hubdevice_uuid=hubdevice_uuid, subdevice_id=subdevice_id, status=status, last_active_time=last_active_time, manager=manager)
        self.__schedule_b_mode: Dict = {}
        self.__timeSync: Dict = {}
        self.__mode: Dict = {}
        self.__temperature: Dict = {}
        self.__adjust: Dict = {}

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
        return None

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

    async def async_update(self,
                           timeout: Optional[float] = None,
                           *args,
                           **kwargs) -> None:
        # Let's call the super implementation first (bubbling up). This is useful
        # when we are nesting multiple mixins and need to handle an event at multiple levels
        await super().async_update()

        # To update entirely the state of this device, we just need to trigger the MTS100_ALL command.
        result = await self._execute_command(method="GET",
                                                  namespace=Namespace.HUB_MTS100_ALL,
                                                  payload={'all': [{'id': self.subdevice_id}]},
                                                  timeout=timeout)

        # Retrieve the sub-device specific data and update the status
        found = False
        subdevices_states = result.get('all')
        if not isinstance(subdevices_states, List):
            _LOGGER.error(f"Failed to get MTS100 data for subdevice {self.subdevice_id}. Returned command result is not a list.")
            return

        for subdev_state in subdevices_states:
            subdev_id = subdev_state.get('id')
            if subdev_id != self.subdevice_id:
                continue
            found = True
            await self._async_handle_mts100_all(data=subdev_state)
            break

        if not found:
            _LOGGER.error(f"Failed to get MTS100 data for subdevice {self.subdevice_id}.")

    async def async_notify_hub_update(self, data: Dict):
        await super().async_notify_hub_update(data=data)
        # TODO: shall we intercept any state here?
        pass

    async def _async_handle_push_notification(self, namespace: str, data: dict) -> bool:
        # Always call the parent handler when done with local specific logic. This gives the opportunity to all
        # ancestors to catch all events.
        parent_handled = await super()._async_handle_push_notification(namespace=namespace, data=data)

        locally_handled = False
        if namespace == Namespace.HUB_MTS100_ALL:
            # TODO: handle this
            pass
        elif namespace == Namespace.HUB_MTS100_MODE.value:
            update_element = self._prepare_push_notification_data(data=data)
            if update_element is not None:
                self.__mode.update(update_element)
                locally_handled = True
        elif namespace == Namespace.HUB_MTS100_TEMPERATURE.value:
            update_element = self._prepare_push_notification_data(data=data)
            if update_element is not None:
                self.__temperature.update(update_element)
                self.__temperature['latestSampleTime'] = datetime.utcnow().timestamp()
                locally_handled = True
        elif namespace == Namespace.HUB_TOGGLEX.value:
            # It looks like MTS100 is also in charge of handling TOGGLEX updates
            update_element = self._prepare_push_notification_data(data=data)
            if update_element is not None:
                if 'onoff' in update_element:
                    self.__temperature['heating'] = update_element['onoff']
                    locally_handled = True

        return locally_handled or parent_handled

    async def _async_handle_mts100_all(self, data: Dict):
        """
        Handles the HUB_MTS100_PAYLOAD
        :param data:
        :return:
        """
        # The MTS100 payload brings a lot of information.

        # The online state might collide with the info from HUB or from the SystemOnline Mixin.
        #  However, we consider this last info to be the most accurate as it comes from the device itself
        if 'online' in data:
            online_data = data['online']
            # NOTE: we are accessing the "online" and "last_active_time" attributes at BASE DEVICE LEVEL here,
            # that is why we use the single "_" rather than the "__" prefix
            self._online = OnlineStatus(online_data.get('status', -1))
            last_active_time = online_data.get('lastActiveTime')
            if last_active_time is not None:
                self._last_active_time = last_active_time

        # The following attributes are instead private to this mixin
        self.__schedule_b_mode = data.get('scheduleBMode', {})
        self.__timeSync = data.get('timeSync', {})
        self.__mode.update(data.get('mode', {}))
        self.__temperature.update(data.get('temperature', {}))
        self.__temperature['latestSampleTime'] = datetime.utcnow().timestamp()
        self.__adjust.update(data.get('temperature', {}))
        self.__adjust['latestSampleTime'] = datetime.utcnow().timestamp()

    async def async_get_temperature(self, timeout: Optional[float] = None, *args, **kwargs) -> Optional[
        float]:
        """
        Polls the device in order to retrieve the latest temperature info.
        You should not use this method so ofter: instead, rely on `last_sampled_temperature` when a cached
        value is ok.

        :return:
        """
        res = await self._execute_command(method="GET", namespace=Namespace.HUB_MTS100_TEMPERATURE,
                                               payload={'temperature': [{"id": self.subdevice_id}]}, timeout=timeout)
        if not isinstance(res, Dict):
            _LOGGER.debug("The returned HUB_MTS100_TEMPERATURE command is not a Dict.")
            return None

        samples = res.get('temperature')
        if not isinstance(samples, List):
            _LOGGER.error(f"Expecting a list from HUB_MTS100_TEMPERATURE command, returned value was {samples}.")
            return None

        for d in samples:
            if d.get('id') == self.subdevice_id:
                del d['id']
                self.__temperature.update(d)
                self.__temperature['latestSampleTime'] = datetime.utcnow().timestamp()
                break

        return self.last_sampled_temperature

    async def async_set_mode(self, mode: ThermostatV3Mode, timeout: Optional[float] = None, *args,
                             **kwargs) -> None:
        payload = {'mode': [{'id': self.subdevice_id, 'state': mode.value}]}
        await self._execute_command(method='SET', namespace=Namespace.HUB_MTS100_MODE, payload=payload,
                                         timeout=timeout)
        self.__mode['state'] = mode.value

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

    async def async_set_preset_temperature(self, preset: str, temperature: float,
                                           timeout: Optional[float] = None,
                                           *args,
                                           **kwargs) -> None:
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
        await self._execute_command(method="SET", namespace=Namespace.HUB_MTS100_TEMPERATURE,
                                         payload={'temperature': [{'id': self.subdevice_id, preset: target_temp}]},
                                         timeout=timeout)

        # Update local state
        self.__temperature[preset] = target_temp

    async def async_set_target_temperature(self, temperature: float, timeout: Optional[float] = None,
                                           *args,
                                           **kwargs) -> None:
        # The API expects the target temperature in DECIMALS, so we need to multiply the user's input by 10
        target_temp = temperature * 10
        payload = {'temperature': [{'id': self.subdevice_id, 'custom': target_temp}]}
        await self._execute_command(method='SET', namespace=Namespace.HUB_MTS100_TEMPERATURE, payload=payload,
                                         timeout=timeout)
        # Update local state
        self.__temperature['currentSet'] = target_temp

    async def async_get_adjust(self, timeout: Optional[float] = None, *args, **kwargs) -> Optional[float]:
        """
        :return:
        """
        res = await self._execute_command(method="GET", namespace=Namespace.HUB_MTS100_ADJUST,
                                               payload={'adjust': [{"id": self.subdevice_id}]}, timeout=timeout)
        if not isinstance(res, Dict):
            _LOGGER.debug("The returned HUB_MTS100_ADJUST command is not a Dict.")
            return None
        samples = res.get('adjust')
        if not isinstance(samples, List):
            _LOGGER.error(f"Expecting a list from HUB_MTS100_ADJUST command. Result was: {samples}")
            return None
        for d in samples:
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

        return float(adjust) / 100.0

    async def async_set_adjust(self, temperature: float, timeout: Optional[float] = None) -> None:
        # The API expects the adjust temperature in HUNDREDS (not consistent with the temperature set), so we need to multiply the user's input by 100
        # N.B. the App enforces on the frontend a limit on the adjustment (+/- 5 C°), tests show there is no limit on the API
        adjust_temp = temperature * 100
        payload = {'adjust': [{'id': self.subdevice_id, 'temperature': adjust_temp}]}
        await self._execute_command(method='SET', namespace=Namespace.HUB_MTS100_ADJUST, payload=payload,
                                         timeout=timeout)
        # Update local state
        self.__adjust.update({'temperature': adjust_temp})
        self.__adjust['latestSampleTime'] = datetime.utcnow().timestamp()
