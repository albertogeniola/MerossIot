import logging
from datetime import datetime
from typing import Optional, Dict, List

from meross_iot.controller.device import GenericSubDevice
from meross_iot.model.enums import Namespace, OnlineStatus

_LOGGER = logging.getLogger(__name__)


class Ms100Mixin(GenericSubDevice):
    """
    Mixin class that provides temperature/humidity sensor features for devices like MS100.
    """

    def __init__(self, hubdevice_uuid: str, subdevice_id: str, status: int, last_active_time: int, manager, **kwargs):
        super().__init__(hubdevice_uuid=hubdevice_uuid, subdevice_id=subdevice_id, status=status,
                         last_active_time=last_active_time, manager=manager,**kwargs)
        self.__temperature: Dict = {}
        self.__humidity: Dict = {}
        self.__samples: List = []

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
        Minimum supported temperature that this device can report

        :return: float value, minimum supported temperature, if available
        """
        return self.__temperature.get('min')

    @property
    def max_supported_temperature(self) -> Optional[float]:
        """
        Maximum supported temperature that this device can report
        """
        return self.__temperature.get('max')

    async def async_update(self,
                           timeout: Optional[float] = None,
                           *args,
                           **kwargs) -> None:
        """
        Updates the state of the sensor by fetching the latest status from the hub.
        Calling this method on the SubDevice class, will only trigger data-fetching for the specific
        device. Call the async_update() method at hub level if you want to update all SubDevices
        states at the same time.
        """
        # Let's call the super implementation first (bubbling up). This is useful
        # when we are nesting multiple mixins and need to handle an event at multiple levels
        await super().async_update()

        # We also need to trigger an update request for this specific sub-device
        result = await self._execute_command(method="GET",
                                                  namespace=Namespace.HUB_SENSOR_ALL,
                                                  payload={'all': [{'id': self.subdevice_id}]},
                                                  timeout=timeout)

        # Update device internal state
        found = False
        subdevices_states = result.get('all')
        if not isinstance(subdevices_states, List):
            _LOGGER.error(f"Failed to get MS100 data for subdevice {self.subdevice_id}. Returned command result is not a list.")
            return

        for subdev_state in subdevices_states:
            subdev_id = subdev_state.get('id')
            if subdev_id != self.subdevice_id:
                continue
            found = True
            self._handle_ms100_all(data=subdev_state)
            break

        if not found:
            _LOGGER.error(f"Failed to get MS100 data for subdevice {self.subdevice_id}.")

    async def async_notify_hub_update(self, data: Dict) -> bool:
        """
        This method is called by the HubMixin whenever a full update (SYSTEM_ALL) is received at hub-level.
        This allows the library to be more efficient: whenever you need to update the state of all SubDevices
        attached to a hub, just call the hub's async_update() and that will fetch and update the state of
        all related SubDevices.
        :param data: Contains the data as per SYSTEM_ALL digest key.
        :return: True if the state was handled, False otherwise
        """
        super_handled = await super().async_notify_hub_update(data=data)
        locally_handled = False
        if 'ms100' in data:
            self._handle_ms100_all(data=data)
            locally_handled = True
        return super_handled or locally_handled

    async def _async_handle_push_notification(self, namespace: str, data: dict) -> bool:
        """
        Handles SubDevice state update based on PushNotifications.
        Mixins can override this method in order to catch specific PushNotifications
        and update their internal state accordingly.
        :param namespace:
        :param data:
        :return:
        """
        # Always call the parent handler when done with local specific logic. This gives the opportunity to all
        # ancestors to catch all events.
        parent_handled = await super()._async_handle_push_notification(namespace=namespace, data=data)

        locally_handled = False
        if namespace == Namespace.HUB_SENSOR_TEMPHUM.value:
            self._handle_ms100_all(data=data)
            locally_handled = True

        return parent_handled or locally_handled

    def _handle_ms100_all(self, data: Dict):
        """
        Handles the HUB_SENSOR_ALL and HUB_SENSOR_TEMPHUM data payload, updating temperature and humidity readings.
        :param data: data payload
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
