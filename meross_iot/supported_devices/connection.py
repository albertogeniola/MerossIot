import datetime
from threading import RLock, Condition

from meross_iot.supported_devices.client_status import ClientStatus
from meross_iot.supported_devices.exceptions.StatusTimeoutException import StatusTimeoutException
from meross_iot.supported_devices.timeouts import SHORT_TIMEOUT


class ConnectionManager(object):
    # The connection status of the device is represented by the following variable.
    # It is protected by the following variable, called _client_connection_status_lock.
    # The child classes should never change/access these variables directly, though.
    _status = None
    _lock = None

    # This condition object is used to synchronize multiple threads waiting for the connection to
    # get into a specific state.
    _status_condition = None

    def __init__(self):
        self._lock = RLock()
        self._status_condition = Condition(self._lock)
        self._status = ClientStatus.INITIALIZED

    def get_status(self):
        with self._status_condition:
            return self._status

    def update_status(self, status):
        with self._status_condition:
            self._status = status
            self._status_condition.notify_all()

    def check_status(self, expected_status):
        with self._lock:
            return expected_status == self._status

    def check_status_in(self, expected_statuses):
        with self._lock:
            return self._status in expected_statuses

    def wait_for_status(self, expected_status, timeout=SHORT_TIMEOUT):
        start_time = datetime.datetime.now()
        with self._status_condition:
            while self._status != expected_status:
                elapsed = datetime.datetime.now().timestamp() - start_time.timestamp()
                to = timeout - elapsed
                timeout_hit = to < 0 or not self._status_condition.wait(to)

                if timeout_hit:
                    # An error has occurred
                    raise StatusTimeoutException("Error while waiting for status %s. Last status is: %s" %
                                                 (expected_status, self._status))
