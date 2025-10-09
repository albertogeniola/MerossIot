import logging
from datetime import datetime
from typing import Optional, TypeVar, Generic, Dict

from meross_iot.controller.subdevice_mixins import GenericSubDeviceProtocol
from meross_iot.model.enums import Namespace, OnlineStatus

_LOGGER = logging.getLogger(__name__)

T_SubDevice = TypeVar('T_SubDevice', bound=GenericSubDeviceProtocol)


class Ms100Mixin(Generic[T_SubDevice]):
    """
    This class maps the functionality offered by the sensors like MS100.
    """

    def __init__(self: T_SubDevice, hubdevice_uuid: str, subdevice_id: str, status: int, last_active_time: int, manager,
                 **kwargs):

        super().__init__(hubdevice_uuid=hubdevice_uuid, subdevice_id=subdevice_id, status=status,
                         last_active_time=last_active_time, manager=manager, **kwargs)
        self.__temperature = {}
        self.__humidity = {}
        self.__samples = []

    @property
    def last_sampled_temperature(self: T_SubDevice) -> Optional[float]:
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
    def last_sampled_humidity(self: T_SubDevice) -> Optional[float]:
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
    def last_sampled_time(self: T_SubDevice) -> Optional[datetime]:
        """
        UTC datetime when the latest update has been sampled by the sensor

        :return: latest sampling time in UTC, if available
        """
        timestamp = self.__temperature.get('latestSampleTime')
        if timestamp is None:
            return None

        return datetime.utcfromtimestamp(timestamp)

    @property
    def min_supported_temperature(self: T_SubDevice) -> Optional[float]:
        """
        Maximum supported temperature that this device can report

        :return: float value, maximum supported temperature, if available
        """
        return self.__temperature.get('min')

    @property
    def max_supported_temperature(self: T_SubDevice) -> Optional[float]:
        """
        Minimum supported temperature that this device can report
        """
        return self.__temperature.get('max')

    async def async_update(self: T_SubDevice,
                           timeout: Optional[float] = None,
                           *args,
                           **kwargs) -> None:

        # Let's call the super implementation first (bubbling up). This is useful
        # when we are nesting multiple mixins and need to handle an event at multiple levels
        await super().async_update()

        # We also need to trigger an update request for this specific sub-device
        result = await self._hub._execute_command(method="GET",
                                                  namespace=Namespace.HUB_SENSOR_ALL,
                                                  payload={'all': [{'id': self.subdevice_id}]},
                                                  timeout=timeout)

        # Update device internal state
        found = False
        subdevices_states = result.get('all')
        for subdev_state in subdevices_states:
            subdev_id = subdev_state.get('id')
            if subdev_id != self.subdevice_id:
                continue
            found = True
            await self._async_handle_ms100_all(data=subdev_state)
            break

        if not found:
            _LOGGER.error(f"Failed to get MS100 data for subdevice {self.subdevice_id}.")

    async def async_notify_hub_update(self: T_SubDevice, data: Dict):
        await super().async_notify_hub_update(data=data)
        # TODO: shall we intercept any state here?
        pass

    async def _async_handle_push_notification(self: T_SubDevice, namespace: str, data: dict) -> bool:
        # Always call the parent handler when done with local specific logic. This gives the opportunity to all
        # ancestors to catch all events.
        parent_handled = await super()._async_handle_push_notification(namespace=namespace, data=data)

        locally_handled = False
        if namespace == Namespace.HUB_SENSOR_TEMPHUM.value:
            latest_temperature = data.get('latestTemperature')
            latest_humidity = data.get('latestHumidity')
            synced_time = data.get('syncedTime')
            samples = data.get('sample')
            if synced_time is not None and (
                    self.last_sampled_time is None or synced_time > self.last_sampled_time.timestamp()):
                self.__temperature['latestSampleTime'] = synced_time
                self.__temperature['latest'] = latest_temperature
                self.__humidity['latestSampleTime'] = synced_time
                self.__humidity['latest'] = latest_humidity
            self.__samples.clear()
            for sample in samples:
                temp, hum, from_ts, to_ts = sample
                self.__samples.append({
                    'from_ts': from_ts,
                    'to_ts': to_ts,
                    'temperature': float(temp) / 10,
                    'humidity': float(hum) / 10
                })
            else:
                _LOGGER.debug("Skipping temperature update as synched time is None or old compared to the latest data")
            locally_handled = True
        elif namespace == Namespace.HUB_SENSOR_ALERT.value:
            locally_handled = False
            # TODO: not yet implemented

        return parent_handled or locally_handled

    async def _async_handle_ms100_all(self: T_SubDevice, data: Dict):
        """
        Handles the HUB_MS100_ALL PAYLOAD
        :param data:
        :return:
        """
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
        if 'temperature' in data:
            self.__temperature.update(data['temperature'])
        if 'humidity' in data:
            self.__humidity.update(data['humidity'])
