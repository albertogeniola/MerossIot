import time
from collections import deque
from datetime import timedelta
from typing import Optional, Deque, Dict, ItemsView

from meross_iot.model.http.error_codes import ErrorCodes


class HttpRequestSample:
    """
    Helper class to hold a single request the http API server
    """
    def __init__(self,
                 method: str,
                 url: str,
                 http_response_code: int,
                 api_response_code: ErrorCodes,
                 timestamp: Optional[float] = None):

        self._method = method
        self._url = url
        self._http_response_code = http_response_code
        self._api_response_code = api_response_code
        self._ts = timestamp

    @property
    def method(self):
        """
        HTTP Method
        :return:
        """
        return self._method

    @property
    def url(self):
        """
        URL
        :return:
        """
        return self._url

    @property
    def http_response_code(self):
        """
        HTTP response code
        :return: 
        """
        return self._http_response_code

    @property
    def api_response_code(self) -> ErrorCodes:
        """
        Meross HTTP API response code
        :return:
        """
        return self._api_response_code

    @property
    def timestamp(self):
        """
        Timestamp of the request
        :return:
        """
        return self._ts


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


class HttpStat:
    """
    Helper class that handles HTTP stats result for a single URL
    """
    def __init__(self):
        self._total_api_calls = 0
        self._by_http_response_code: Dict[int, int] = {}
        self._by_api_response_code: Dict[ErrorCodes, int] = {}

    def add(self, sample: HttpRequestSample) -> None:
        self._total_api_calls += 1

        # Aggregate by HTTP response code
        if sample.http_response_code not in self._by_http_response_code:
            self._by_http_response_code[sample.http_response_code] = 1
        else:
            self._by_http_response_code[sample.http_response_code] += 1

        # Aggregate by API response code
        if sample.api_response_code not in self._by_api_response_code:
            self._by_api_response_code[sample.api_response_code] = 1
        else:
            self._by_api_response_code[sample.api_response_code] += 1

    @property
    def total_calls(self) -> int:
        """
        Total number of calls for this URL
        """
        return self._total_api_calls

    def by_http_reponse_code(self) -> ItemsView[int, int]:
        """
        Number of calls for this url aggregated by HTTP response code
        """
        return self._by_http_response_code.items()

    def by_api_status_code(self) -> ItemsView[ErrorCodes, int]:
        """
        Number of calls for this url aggregated by API response status code
        """
        return self._by_api_response_code.items()

    def __repr__(self):
        http_reponses = sorted(self._by_http_response_code.items(), key=lambda item: item[1], reverse=True)
        http_details = ", ".join([f"{code}: {calls}" for code, calls in http_reponses])
        api_statuses = sorted(self._by_http_response_code.items(), key=lambda item: item[1], reverse=True)
        api_details = ", ".join([f"{code}: {calls}" for code, calls in api_statuses])
        return f"{self.total_calls} ({http_details}; {api_details})"


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


class HttpStatsResult:
    """
    Helper class that handles HTTP requests stats result
    """
    def __init__(self):
        self._global = HttpStat()
        self._by_url: Dict[str, HttpStat] = {}

    def add(self, sample: HttpRequestSample):
        self._global.add(sample)
        byurl = self._by_url.get(sample.url)
        if byurl is None:
            byurl = HttpStat()
            self._by_url[sample.url] = byurl
        byurl.add(sample)

    @property
    def global_stats(self) -> HttpStat:
        """
        Total number of calls
        """
        return self._global

    def stats_by_url(self, url: str) -> Optional[HttpStat]:
        """
        Returns the statistics of a specific url
        """
        return self._by_url.get(url)

    def device_stats(self) -> ItemsView[str, HttpStat]:
        """
        Statistics aggregated by URL
        """
        return self._by_url.items()

    def __repr__(self):
        top_urls = sorted(self._by_url.items(), key=lambda item: item[1].global_stats, reverse=True)
        url_rerp = ",\n".join([f"{url}: {stats}" for url, stats in top_urls])
        return f"--------\n" \
               f"Global Calls: {self._global.total_calls}\n" \
               f"{url_rerp}\n" \
               f"--------\n"


class ApiStatsResult:
    """
    Helper class that handles API stats result
    """
    def __init__(self):
        self._global = ApiStat()
        self._by_uuid: Dict[str, ApiStat] = {}

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

    def device_stats(self) -> ItemsView[str, ApiStat]:
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


class HttpStatsCounter:
    """
    Helper class to keep track and calculate statistics for sent HTTP requests
    """
    def __init__(self, max_samples=1000):
        self._samples: Deque[HttpRequestSample] = deque([], maxlen=max_samples)

    def notify_http_request(self, request_url: str, method: str, http_response_code: int, api_response_code: Optional[ErrorCodes]):
        sample = HttpRequestSample(
            url=request_url,
            method=method,
            http_response_code=http_response_code,
            api_response_code=api_response_code,
            timestamp=time.time()
        )
        self._samples.append(sample)

    def _get_stats(self, samples: Deque[HttpRequestSample], time_window: timedelta = timedelta(minutes=1)) -> HttpStatsResult:
        result = HttpStatsResult()
        lower_limit = time.time() - time_window.total_seconds()
        for sample in reversed(samples):
            if sample.timestamp > lower_limit:
                result.add(sample)

        return result

    def get_stats(self, time_window: timedelta = timedelta(minutes=1)) -> HttpStatsResult:
        """
        Returns the statistics of sent MQTT messages to the MQTT broker
        """
        return self._get_stats(samples=self._samples, time_window=time_window)


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

