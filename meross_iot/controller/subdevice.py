from typing import Optional, Tuple, Iterable
from meross_iot.controller.device import GenericSubDevice
from meross_iot.model.enums import Namespace, OnlineStatus
import logging

from meross_iot.model.push.generic import GenericPushNotification

_LOGGER = logging.getLogger(__name__)


class Mts100v3Valve(GenericSubDevice):
    def __init__(self, hubdevice_uuid: str, subdevice_id: str, manager, **kwargs):
        super().__init__(hubdevice_uuid, subdevice_id, manager, **kwargs)
        self.__togglex = {}
        self.__timeSync = None
        self.__mode = {}
        self.__temperature = {}
        self._schedule_b_mode = None
        self._last_active_time = None

    async def _execute_command(self, method: str, namespace: Namespace, payload: dict, timeout: float = 5) -> dict:
        raise NotImplementedError("This method should never be called directly for subdevices.")

    def handle_push_notification(self, namespace: Namespace, data: dict) -> bool:
        locally_handled = False
        if namespace == Namespace.HUB_ONLINE:
            update_element = self.__prepare_push_notification_data(key='online', data=data)
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
            locally_handled = True
        elif namespace == Namespace.HUB_TOGGLEX:
            update_element = self.__prepare_push_notification_data(key='togglex', data=data)
            self.__togglex.update(update_element)
            locally_handled = True
        elif namespace == Namespace.HUB_MTS100_MODE:
            update_element = self.__prepare_push_notification_data(key='mode', data=data)
            self.__mode.update(update_element)
            locally_handled = True
        elif namespace == Namespace.HUB_MTS100_TEMPERATURE:
            update_element = self.__prepare_push_notification_data(key='temperature', data=data)
            self.__temperature.update(update_element)
            locally_handled = True

        # Always call the parent handler when done with local specific logic. This gives the opportunity to all
        # ancestors to catch all events.
        parent_handled = super().handle_push_notification(namespace=namespace, data=data)
        return locally_handled or parent_handled

    def __prepare_push_notification_data(self, key, data):
        multiple = data.get(key, [])
        if len(multiple) != 1:
            raise ValueError("Temperature event does not provide exactly one update element")
        update_element = multiple[0].copy()
        del update_element['id']
        return update_element

    def is_on(self) -> Optional[bool]:
        return self.__togglex.get('onoff') == 1

    async def async_turn_off(self, *args, **kwargs):
        await self._hub._execute_command("SET", Namespace.HUB_TOGGLEX, {'togglex': [{"id": self.subdevice_id,
                                                                                     "onoff": 0, "channel": 0}]})
        # Assume the command was ok, so immediately update the internal state
        self.__togglex['onoff'] = 0

    async def async_turn_on(self, *args, **kwargs):
        await self._hub._execute_command("SET", Namespace.HUB_TOGGLEX, {'togglex': [{"id": self.subdevice_id,
                                                                                     "onoff": 1, "channel": 0}]})
        # Assume the command was ok, so immediately update the internal state
        self.__togglex['onoff'] = 1

    async def async_toggle(self, *args, **kwargs):
        if self.is_on():
            await self.async_turn_off()
        else:
            await self.async_turn_on()

    @property
    def ambient_temperature(self) -> Optional[float]:
        """
        Current room temperature in Celsius degrees.
        :return:
        """
        temp = self.__temperature.get('room')
        if temp is not None:
            return float(temp) / 10.0
        else:
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

    def get_preset_temperature(self, preset: str) -> Optional[float]:
        """
        Returns the current set temperature for the given preset.
        :param preset:
        :return:
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
        :return:
        """
        return 'custom', 'comfort', 'economy', 'away'

    async def async_set_preset_temperature(self, preset: str, temperature: float) -> None:
        """
        Sets the preset temperature configuration.
        :param preset:
        :param temperature:
        :return:
        """
        if preset not in self.get_supported_presets():
            raise ValueError(f"Preset {preset} is not supported by this device. "
                             f"Valid presets are: {self.get_supported_presets()}")
        target_temp = temperature * 10
        await self._hub._execute_command(method="SET", namespace=Namespace.HUB_MTS100_TEMPERATURE, payload={
            'temperature': [{
                'id': self.subdevice_id,
                preset: target_temp
            }]})

        # Update local state
        self.__temperature[preset] = target_temp

    async def async_set_target_temperature(self, temperature: float) -> None:
        # The API expects the target temperature in DECIMALS, so we need to multiply the user's input by 10
        target_temp = temperature * 10
        payload = {'temperature': [{'id': self.subdevice_id, 'custom': target_temp}]}
        await self._hub._execute_command(method='SET',
                                          namespace=Namespace.HUB_MTS100_TEMPERATURE,
                                          payload=payload)
        # Update local state
        self.__temperature['currentSet'] = target_temp
