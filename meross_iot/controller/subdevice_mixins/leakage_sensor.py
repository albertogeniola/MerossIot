import logging
from collections import deque
from typing import Optional, List, Dict, Any

from meross_iot.controller.device import GenericSubDevice
from meross_iot.model.enums import Namespace

_LOGGER = logging.getLogger(__name__)


class LeakageSensorMixin(GenericSubDevice):
    """
    Mixin class that provides support for water leakage sensors (MS400).
    """

    def __init__(self, hubdevice_uuid:str, subdevice_id:str, status:int, last_active_time:int, manager, **kwargs):
        super().__init__(hubdevice_uuid=hubdevice_uuid, subdevice_id=subdevice_id, status=status, last_active_time=last_active_time, manager=manager, **kwargs)
        self.__water_leak_state: Optional[bool] = None
        # Represents the current state

        self.__last_event_ts: Optional[int] = None
        # Represents the timestamp of the last sample (current state sampling)

        self.__cached_events: deque = deque(maxlen=30)
        # Last N samples we collected

        self.__last_waterleak_event_ts: Optional[int] = None
        # Timestamp of the last waterleak event

    @property
    def is_leaking(self) -> Optional[bool]:
        """
        Returns the latest updated state available for the water leak sensor, if available.
        """
        return self.__water_leak_state == 1

    @property
    def latest_sample_time(self) -> Optional[int]:
        """
        Returns the timestamp (GMT) of the latest available sampling.
        """
        return self.__last_event_ts

    @property
    def latest_detected_water_leak_ts(self) -> Optional[int]:
        """
        Return the timestamp (GMT) of the latest time the sensor sampled a water leak.
        """
        return self.__last_waterleak_event_ts

    @property
    def get_last_events(self) -> List[Dict]:
        """
        Returns the last cached items
        """
        return list(self.__cached_events)

    async def async_update(self,
                           timeout: Optional[float] = None,
                           *args,
                           **kwargs) -> None:
        """
        Updates the state of the leakage sensor by fetching the latest status from the hub.
        Calling this method on the SubDevice class, will only trigger data-fetching for the specific
        device. Call the async_update() method at hub level if you want to update all SubDevices
        states at the same time.
        """
        # Let's call the super implementation first (bubbling up). This is useful
        # when we are nesting multiple mixins and need to handle an event at multiple levels
        await super().async_update()

        # Leakage sensor are interested in the HUB_SENSOR_LEAKGE state.
        result = await self._execute_command(method="GET",
                                                  namespace=Namespace.HUB_SENSOR_WATERLEAK,
                                                  payload={'waterLeak': [{'id': self.subdevice_id}]},
                                                  timeout=timeout)

        # When we issue a command to a subdevice, we might get a response that contains the state of
        # multiple subdevices. So, we need to find the one that is specific to our own.
        sensor_data = result.get('waterLeak')
        if sensor_data is None:
            _LOGGER.error(f"Missing waterLeak key within result data: {result}.")
            return

        data = None
        for d in sensor_data:
            if d.get('id') == self.subdevice_id:
                data = d
                break

        if data is None:
            _LOGGER.error(
                f"Returned data is missing the SubDevice id we are looking for '{self.subdevice_id}'. Data: {data}.")
            return

        self._handle_waterleak_update(data=data)

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
        if 'waterLeak' in data:
            self._handle_waterleak_update(data=data['waterLeak'])
            locally_handled = True
        return super_handled or locally_handled

    async def _async_handle_push_notification(self, namespace: Namespace, data: Any) -> bool:
        """
        Handles SubDevice state update based on PushNotifications.
        Mixins can override this method in order to catch specific PushNotifications
        and update their internal state accordingly.
        :param namespace:
        :param data:
        :return:
        """
        # Let's call the super implementation first (bubbling up). This is useful
        # when we are nesting multiple mixins and need to handle an event at multiple levels
        parent_handled = await super()._async_handle_push_notification(namespace=namespace, data=data)

        locally_handled = False
        if namespace == Namespace.HUB_SENSOR_WATERLEAK:
            self._handle_waterleak_update(data=data)
            locally_handled = True

        return locally_handled or parent_handled

    def _handle_waterleak_update(self, data: Dict):
        """
        Handles the HUB_SENSOR_WATERLEAK data payload.
        :param data: HUB_SENSOR_WATERLEAK data payload
        """
        leaking = data.get('latestWaterLeak')
        if leaking is None:
            _LOGGER.warning("Missing keyword 'latestWaterLeak' in data payload.")
            return

        timestamp = data.get('latestSampleTime')
        if timestamp is None:
            _LOGGER.warning("Missing keyword 'latestSampleTime' in data payload.")
            return

        # If handling an event with an older timestamp than the one we have, just discard it.
        if self.latest_sample_time is not None and timestamp <= self.latest_sample_time:
            return

        # If this is the first update or if it's more recent than the last we have, update the current state.
        if self.__last_event_ts is None or timestamp >= self.__last_event_ts:
            self.__last_event_ts = timestamp
            self.__water_leak_state = leaking

        # If the event is a leak and is more recent than the latest leak event, update it.
        if leaking and (self.__last_waterleak_event_ts is None or timestamp >= self.__last_waterleak_event_ts):
            self.__last_waterleak_event_ts = timestamp

        # In any case, register the event in the queue
        self.__cached_events.append({
            "leaking": leaking,
            "timestamp": timestamp
        })
