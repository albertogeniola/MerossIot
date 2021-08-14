import time
from collections import deque
from datetime import timedelta
from typing import Optional, Deque, Dict, ItemsView, Any


class ApiCallSample:
    """
    Helper class to hold a single call to the mqtt broker
    """
    def __init__(self,
                 device_uuid: str,
                 namespace: str,
                 method: str,
                 timestamp: Optional[float] = None):

        self._uuid = device_uuid
        self._ns = namespace
        self._method = method
        self._ts = timestamp

    @property
    def device_uuid(self):
        """
        Target Device UUID for the message
        """
        return self._uuid

    @property
    def namespace(self):
        """
        Target Namespace for the message
        """
        return self._ns

    @property
    def method(self):
        """
        Target Method for the message
        """
        return self._method

    @property
    def timestamp(self):
        """
        When the record has been registered
        """
        return self._ts


class ApiStat:
    """
    Helper class that handles API stats result for a single device
    """
    def __init__(self):
        self._total_api_calls = 0
        self._by_method_namespace: Dict[str, int] = {}

    def add(self, sample: ApiCallSample) -> None:
        self._total_api_calls += 1

        method_ns = f"{sample.method} {sample.namespace}"
        if method_ns not in self._by_method_namespace:
            self._by_method_namespace[method_ns] = 1
        else:
            self._by_method_namespace[method_ns] += 1

    @property
    def total_calls(self) -> int:
        """
        Total number of calls for this device
        """
        return self._total_api_calls

    def by_method_namespace(self) -> ItemsView[str, int]:
        """
        Number of calls for this device aggregated by Method/Namespace
        """
        return self._by_method_namespace.items()

    def __repr__(self):
        top_calls = sorted(self._by_method_namespace.items(), key=lambda item: item[1], reverse=True)
        details = ", ".join([f"{method}: {calls}" for method, calls in top_calls])
        return f"{self.total_calls} ({details})"


class ApiStatsResult:
    """
    Helper class that handles API stats result
    """
    def __init__(self):
        self._global = ApiStat()
        self._by_uuid: Dict[ApiStat] = {}

    def add(self, sample: ApiCallSample):
        self._global.add(sample)
        byuuid = self._by_uuid.get(sample.device_uuid)
        if byuuid is None:
            byuuid = ApiStat()
            self._by_uuid[sample.device_uuid] = byuuid
        byuuid.add(sample)

    @property
    def global_stats(self) -> ApiStat:
        """
        Total number of calls
        """
        return self._global

    def stats_by_uuid(self, device_uuid) -> Optional[ApiStat]:
        """
        Returns the statistics of a specific device UUID
        """
        return self._by_uuid.get(device_uuid)

    def device_stats(self) -> ItemsView[ApiStat, Any]:
        """
        Statistics aggregated by Device UUID
        """
        return self._by_uuid.items()

    def __repr__(self):
        top_devices = sorted(self._by_uuid.items(), key=lambda item: item[1].global_stats, reverse=True)
        device_rerp = ",\n".join([f"{uuid}: {stats}" for uuid, stats in top_devices])
        return f"--------\n" \
               f"Global Calls: {self._global.total_calls}\n" \
               f"{device_rerp}\n" \
               f"--------\n"


class ApiCounter:
    """
    Helper class to keep track and calculate statistics for sent MQTT message
    """
    def __init__(self, max_samples=1000):
        self.api_calls: Deque[ApiCallSample] = deque([], maxlen=max_samples)
        self.delayed_calls: Deque[ApiCallSample] = deque([], maxlen=max_samples)
        self.dropped_calls: Deque[ApiCallSample] = deque([], maxlen=max_samples)

    def notify_api_call(self, device_uuid: str, namespace: str, method: str):
        """
        Method called internally by the manager itself, whenever a message is sent to the
        MQTT broker.
        """
        sample = ApiCallSample(
            device_uuid=device_uuid,
            namespace=namespace,
            method=method,
            timestamp=time.time()
        )
        self.api_calls.append(sample)

    def notify_delayed_call(self, device_uuid: str, namespace: str, method: str):
        """
        Method called internally by the manager itself, whenever a message is delayed instead of being sent to the
        MQTT broker.
        """
        sample = ApiCallSample(
            device_uuid=device_uuid,
            namespace=namespace,
            method=method,
            timestamp=time.time()
        )
        self.delayed_calls.append(sample)

    def notify_dropped_call(self, device_uuid: str, namespace: str, method: str):
        """
        Method called internally by the manager itself, whenever a message is dropped instead of being sent to the
        MQTT broker.
        """
        sample = ApiCallSample(
            device_uuid=device_uuid,
            namespace=namespace,
            method=method,
            timestamp=time.time()
        )
        self.dropped_calls.append(sample)

    def _get_stats(self, api_samples: Deque[ApiCallSample], time_window: timedelta = timedelta(minutes=1)) -> ApiStatsResult:
        result = ApiStatsResult()
        lower_limit = time.time() - time_window.total_seconds()
        for sample in reversed(api_samples):
            if sample.timestamp > lower_limit:
                result.add(sample)

        return result

    def get_api_stats(self, time_window: timedelta = timedelta(minutes=1)) -> ApiStatsResult:
        """
        Returns the statistics of sent MQTT messages to the MQTT broker
        """
        return self._get_stats(api_samples=self.api_calls, time_window=time_window)

    def get_delayed_api_stats(self, time_window: timedelta = timedelta(minutes=1)) -> ApiStatsResult:
        """
        Returns the statistics of delayed MQTT messages to the MQTT broker
        """
        return self._get_stats(api_samples=self.delayed_calls, time_window=time_window)

    def get_dropped_api_stats(self, time_window: timedelta = timedelta(minutes=1)) -> ApiStatsResult:
        """
        Returns the statistics of dropped MQTT messages to the MQTT broker
        """
        return self._get_stats(api_samples=self.dropped_calls, time_window=time_window)

