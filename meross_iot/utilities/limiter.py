from abc import ABC, abstractmethod
from datetime import timedelta
from enum import Enum
from time import time
import logging
from typing import Dict, Tuple

_LIMITER = logging.getLogger("meross_iot.manager.apilimiter")


class BackoffLogic(ABC):
    @abstractmethod
    def reset(self) -> None:
        pass

    @abstractmethod
    def wait_interval(self) -> float:
        pass


class ExponentialBackoff(BackoffLogic):
    def __init__(self, start_backoff_seconds: float, max_backoff_seconds: float):
        self._baseline = start_backoff_seconds
        self._cap = max_backoff_seconds
        self._failures = 0

    def wait_interval(self) -> float:
        current = min(self._baseline * pow(2, self._failures), self._cap)
        self._failures += 1
        return current

    def reset(self) -> None:
        self._failures = 0


class TokenBucketRateLimiterWithBackoff(object):
    """
    Simple implementation of token bucket rate limiter algorithm
    Careful: This class is not thread-safe.
    """

    def __init__(self,
                 window_interval: timedelta,
                 tokens_per_interval: int,
                 max_burst_size: int,
                 backoff_logic: BackoffLogic):
        self._window_interval_seconds = window_interval.total_seconds()
        self._tokens_per_interval = tokens_per_interval
        self._max_burst = max_burst_size
        self._backoff_logic = backoff_logic

        # Let's keep track of limit hits in the ongoing time-window
        self._limit_hits_in_window = 0

        # Set the initial interval end in the past, so that the first iteration is consistent with the following ones
        self._current_window_end = time() - self._window_interval_seconds
        self._remaining_tokens = 0

    def _add_tokens(self):
        # Calculate the number of tokens that we should add.
        # This is calculated as number of intervals we skipped * tokens_per_interval
        # However, we can only add up to max_burst tokens
        now = time()
        if now < self._current_window_end:
            # Do not add tokens for intervals that have been already
            # considered
            return

        # Calculate how many intervals have passed since the end of the previous one
        n_intervals = (now - self._current_window_end) // self._window_interval_seconds + 1
        n_tokens = n_intervals * self._tokens_per_interval
        self._remaining_tokens = min(self._remaining_tokens + n_tokens, self._max_burst)
        self._current_window_end = now + self._window_interval_seconds
        self._limit_hits_in_window = 0

    @property
    def current_over_limit_hits(self) -> int:
        """
        How many calls have been performed, within the time window, above the configured limit.
        Those calls were possibly delayed, aborted.
        :return:
        """
        self._add_tokens()
        return self._limit_hits_in_window

    @property
    def over_limit_percentace(self):
        """
        Represents the percentage of the API calls over the configured limit, with respect to the maximum burst size.
        If the burst size is 100, and in the current time window there were 150 api calls, then 50 o f them are over
        the limit. This property will then return (50 / 100) * 100 -> 50%.
        :return:
        """
        self._add_tokens()
        return (self._limit_hits_in_window / self._max_burst) * 100

    @property
    def current_window_hitrate(self) -> int:
        """
        Number of API cassl performed in the current time-window.
        :return:
        """
        self._add_tokens()
        return self._max_burst - self._remaining_tokens

    @property
    def current_window_capacity(self):
        """
        Percentage of API calls performed in the current time-window with respect to the burst limit.
        For instance, if 90 api calls have been performed over a burst limit of 100, this method returns 90
        (i.e. 90% of the limit capacity reached)
        :return:
        """
        self._add_tokens()
        return (self._limit_hits_in_window / self._max_burst) * 100

    def check_limit_reached(self) -> Tuple[bool, float]:
        # Add tokens if needed
        self._add_tokens()

        if self._remaining_tokens > 0:
            self._remaining_tokens -= 1
            self._backoff_logic.reset()
            return False, 0

        self._limit_hits_in_window += 1
        wait_interval = self._backoff_logic.wait_interval()
        return True, wait_interval


class RateLimitResult(Enum):
    NotLimited = 0,
    GlobalLimitReached = 1,
    PerDeviceLimitReached = 2


class RateLimitResultStrategy(Enum):
    PerformCall = 0,
    DelayCall = 1,
    DropCall = 2


class RateLimitChecker(object):
    """
    Helper class the implements API call limiter.
    This class takes track of API limits per device uuid and at global level (i.e. regardless of the device-uuid).
    """
    def __init__(self,
                 global_burst_rate: int = 6,
                 global_time_window: timedelta = timedelta(seconds=1),
                 global_tokens_per_interval: int = 2,
                 device_burst_rate: int = 1,
                 device_time_window: timedelta = timedelta(seconds=1),
                 device_tokens_per_interval: int = 1,
                 device_max_command_queue: int = 5):
        """
        Constructor
        :param global_burst_rate: Global burst rate, max number of commands that can be executed within the global_time_window
        :param global_time_window: Time window in seconds that is used to aggregate the API counting
        :param global_tokens_per_interval: Number of calls allowed within the time interval at run time (globally)
        :param device_burst_rate: Per device burst rate, max number of commands that can be executed on a specific device within he device_time_window
        :param device_time_window: Time window in seconds that is used to aggregate the API counting for a given device
        :param device_tokens_per_interval: Number of calls allowed within the time interval at run time (per device)
        :param device_max_command_queue: Maximum number of commands that can be delayed for a given device, after which commands are dropped
        """
        # Global limiter configuration
        self._global_limiter = TokenBucketRateLimiterWithBackoff(window_interval=global_time_window,
                                                                 tokens_per_interval=global_tokens_per_interval,
                                                                 max_burst_size=global_burst_rate,
                                                                 backoff_logic=ExponentialBackoff(
                                                                     start_backoff_seconds=0.5,
                                                                     max_backoff_seconds=10
                                                                 ))
        # Device limiters
        self._devices_limiters = {}
        self._device_burst_rate = device_burst_rate
        self._device_time_window = device_time_window
        self._device_tokens_per_interval = device_tokens_per_interval
        self._max_command_queue = device_max_command_queue
        self._current_command_queue_size = {}

    @property
    def global_rate_limiter(self) -> TokenBucketRateLimiterWithBackoff:
        return self._global_limiter

    @property
    def device_limiters(self) -> Dict[str, TokenBucketRateLimiterWithBackoff]:
        return self._devices_limiters

    def check_limits(self, device_uuid: str) -> Tuple[RateLimitResultStrategy, float]:
        """
        Checks the API limit against the configured thresholds
        :param device_uuid: Device for which API call is being called
        :return:
        """
        result, wait_time, overlimit = self._check_limits_internal(device_uuid=device_uuid)
        device_command_queue_size = self._current_command_queue_size[device_uuid]

        if result == RateLimitResult.NotLimited:
            self._dec_command_queue(device_uuid=device_uuid)
            return RateLimitResultStrategy.PerformCall, 0
        elif device_command_queue_size < self._max_command_queue:
            _LIMITER.warning("Api call delayed by %f seconds. Device %s queue size: %d/%d",
                             wait_time,
                             device_uuid,
                             device_command_queue_size,
                             self._max_command_queue)
            self._inc_command_queue(device_uuid=device_uuid)
            return RateLimitResultStrategy.DelayCall, wait_time
        else:
            _LIMITER.error("Api call dropped. Device %s queue size: %d/%d",
                           device_uuid,
                           device_command_queue_size,
                           self._max_command_queue)
            return RateLimitResultStrategy.DropCall, 0

    def _dec_command_queue(self, device_uuid: str):
        if self._current_command_queue_size[device_uuid] > 0:
            self._current_command_queue_size[device_uuid] -= 1

    def _inc_command_queue(self, device_uuid: str):
        self._current_command_queue_size[device_uuid] += 1

    def _check_limits_internal(self, device_uuid: str) -> Tuple[RateLimitResult, float, float]:
        """
        Check is the call can be performed against the preconfigured limits and returns the possible limit that was
        hit, the time to wait before performing again the call and the current over-quota percentage.
        :param device_uuid:
        :return:
        """
        # Check the device limit first
        if device_uuid not in self._devices_limiters:
            self._devices_limiters[device_uuid] = TokenBucketRateLimiterWithBackoff(
                window_interval=self._device_time_window,
                tokens_per_interval=self._device_tokens_per_interval,
                max_burst_size=self._device_burst_rate,
                backoff_logic=ExponentialBackoff(start_backoff_seconds=0.5, max_backoff_seconds=30))
            self._current_command_queue_size[device_uuid] = 0
        device_limiter = self._devices_limiters[device_uuid]
        limit_hit, wait_time = device_limiter.check_limit_reached()
        if limit_hit:
            return RateLimitResult.PerDeviceLimitReached, wait_time, device_limiter.over_limit_percentace

        # Check the global rate limiter
        limit_hit, wait_time = self._global_limiter.check_limit_reached()
        if limit_hit:
            return RateLimitResult.GlobalLimitReached, wait_time, self._global_limiter.over_limit_percentace

        return RateLimitResult.NotLimited, 0, 0
