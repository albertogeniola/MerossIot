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

    def handle_all_update(self, namespace: Namespace, data: dict, *args, **kwargs) -> bool:
        parent_handled = super().handle_all_update(namespace=namespace, data=data, *args, **kwargs)
        locally_handled = False
        if namespace == Namespace.HUB_MTS100_ALL:
            self._last_active_time = data.get('lastActiveTime')
            self._schedule_b_mode = data.get('scheduleBMode')
            self._online = OnlineStatus(data.get('online', {}).get('status', -1))
            self.__togglex.update(data.get('togglex'))
            self.__timeSync = data.get('timeSync')
            self.__mode.update(data.get('mode'))
            self.__temperature.update(data.get('temperature'))

        return parent_handled or locally_handled

    def handle_push_notification(self, namespace: Namespace, data: dict) -> bool:
        locally_handled = False
        if namespace == Namespace.HUB_ONLINE:
            # TODO
            raise NotImplementedError("TODO")
            locally_handled = True

        # Always call the parent handler when done with local specific logic. This gives the opportunity to all
        # ancestors to catch all events.
        parent_handled = super().handle_push_notification(namespace=namespace, data=data)
        return locally_handled or parent_handled

    @property
    def is_on(self) -> Optional[bool]:
        return self.__togglex.get('onoff') == 1

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

    def get_preset_temp(self, preset: str) -> Optional[float]:
        """
        Returns the
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
