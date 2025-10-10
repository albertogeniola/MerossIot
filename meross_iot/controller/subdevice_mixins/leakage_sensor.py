import logging
from collections import deque
from typing import Optional, List, Dict, Any

from meross_iot.controller.device import GenericSubDevice
from meross_iot.model.enums import Namespace

_LOGGER = logging.getLogger(__name__)


class LeakageSensorMixin(GenericSubDevice):
    """
    Mixin implementing leakage sensor SubDevices
    """

    def __init__(self, hubdevice_uuid:str, subdevice_id:str, status:int, last_active_time:int, manager):
        super().__init__(hubdevice_uuid=hubdevice_uuid, subdevice_id=subdevice_id, status=status, last_active_time=last_active_time, manager=manager)
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
        return self.__water_leak_state

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
        return [x for x in self.__cached_events]

    def _handle_water_leak_fresh_data(self, leaking: bool, timestamp: int):
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

    async def async_update(self,
                           timeout: Optional[float] = None,
                           *args,
                           **kwargs) -> None:
        # Let's call the super implementation first (bubbling up). This is useful
        # when we are nesting multiple mixins and need to handle an event at multiple levels
        await super().async_update()

        # Leakage sensor are interested in the HUB_SENSOR_LEAKGE state.
        result = await self._execute_command(method="GET",
                                                  namespace=Namespace.HUB_SENSOR_WATERLEAK,
                                                  payload={'waterLeak': [{'id': self.subdevice_id}]},
                                                  timeout=timeout)
        sensor_data = result.get('waterLeak')
        if sensor_data is None:
            _LOGGER.error(f"Missing waterLeak key within result data: {result}.")
            return
        data = next(filter(lambda x: x['id'] == self.subdevice_id, sensor_data))
        if data is None:
            _LOGGER.error(
                f"Returned data is missing the SubDevice id we are looking for '{self.subdevice_id}'. Data: {data}.")
            return
        self._handle_water_leak_fresh_data(leaking=data.get("latestWaterLeak", 0) == 1,
                                           timestamp=data.get("latestSampleTime"))

    async def async_notify_hub_update(self, data: Dict) -> None:
        await super().async_notify_hub_update(data=data)
        # TODO: shall we intercept any state here?
        pass

    async def _async_handle_push_notification(self, namespace: str, data: Any) -> bool:
        # Let's call the super implementation first (bubbling up). This is useful
        # when we are nesting multiple mixins and need to handle an event at multiple levels
        parent_handled = await super()._async_handle_push_notification(namespace=namespace, data=data)

        locally_handled = False
        if namespace == Namespace.HUB_SENSOR_WATERLEAK.value:
            self._handle_water_leak_fresh_data(leaking=data['latestWaterLeak'] == 1, timestamp=data['latestSampleTime'])
            locally_handled = True

        return locally_handled or parent_handled

    def __repr__(self) -> str:
        return f"<Ms400Device(uuid={self.uuid}, is_leaking={self.is_leaking})>"
