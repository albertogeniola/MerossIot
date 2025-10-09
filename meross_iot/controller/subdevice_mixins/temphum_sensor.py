from datetime import datetime
from typing import Optional

from meross_iot.controller.device import GenericSubDevice
from meross_iot.model.enums import Namespace, OnlineStatus
import logging


_LOGGER = logging.getLogger(__name__)

class TemperatureHumidityMixin(GenericSubDevice):
    """
    This class maps the functionality offered by the sensors like MS100.
    """
    def __init__(self, hubdevice_uuid: str, subdevice_id: str, status: int, last_active_time: int, manager, **kwargs):

        super().__init__(hubdevice_uuid=hubdevice_uuid, subdevice_id=subdevice_id, status=status, last_active_time=last_active_time, manager=manager, **kwargs)
        self.__temperature = {}
        self.__humidity = {}
        self.__samples = []

    async def async_update(self,
                           timeout: Optional[float] = None,
                           *args,
                           **kwargs) -> None:

        # Make sure we issue an update at HUB level first
        await super().async_update()

        # We also need to trigger an update request for this specific sub-device
        result = await self._hub._execute_command(method="GET",
                                                  namespace=Namespace.HUB_SENSOR_ALL,
                                                  payload={'all': [{'id': self.subdevice_id}]},
                                                  timeout=timeout)

        # Retrieve the sub-device specific data and update the status
        subdevices_states = result.get('all')
        for subdev_state in subdevices_states:
            subdev_id = subdev_state.get('id')
            if subdev_id != self.subdevice_id:
                continue
            await self.async_handle_subdevice_notification(namespace=Namespace.HUB_SENSOR_ALL, data=subdev_state)
            break

    async def _async_handle_push_notification(self, namespace: str, data: dict) -> bool:
        parent_handled = await super()._async_handle_push_notification(namespace=namespace, data=data)
        locally_handled = False
        if namespace == Namespace.HUB_ONLINE.value:
            update_element = self._prepare_push_notification_data(data=data, filter_accessor='online')
            if update_element is not None:
                self._online = OnlineStatus(update_element.get('status', -1))
                locally_handled = True

        return parent_handled or locally_handled


    async def async_handle_subdevice_notification(self, namespace: Namespace, data: dict) -> bool:
        locally_handled = False
        if namespace == Namespace.HUB_SENSOR_ALL:
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
                    'temperature': float(temp) / 10,
                    'humidity': float(hum) / 10
                })

            else:
                _LOGGER.debug("Skipping temperature update as synched time is None or old compared to the latest data")
            locally_handled = True
        elif namespace == Namespace.HUB_SENSOR_ALERT:
            locally_handled = False
            # TODO: not yet implemented
        else:
            _LOGGER.warning(f"Could not handle event %s in subdevice %s handler", namespace, self.name)

        # Always call the parent handler when done with local specific logic. This gives the opportunity to all
        # ancestors to catch all events.
        parent_handled = await super()._async_handle_push_notification(namespace=namespace, data=data)
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
