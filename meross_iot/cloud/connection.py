import datetime
from threading import RLock, Condition

from meross_iot.cloud.client_status import ClientStatus
from meross_iot.cloud.exceptions.StatusTimeoutException import StatusTimeoutException
from meross_iot.cloud.timeouts import SHORT_TIMEOUT
from meross_iot.logger import CONNECTION_MANAGER_LOGGER as l
from meross_iot.meross_event import ClientConnectionEvent


class ConnectionStatusManager(object):
    # The connection status of the device is represented by the following variable.
    # It is protected by the following variable, called _client_connection_status_lock.
    # The child classes should never change/access these variables directly, though.
    _status = None
    _lock = None

    # List of callbacks that should be called when an event occurs
    _connection_event_callbacks = None
    _connection_event_callbacks_lock = None

    # This condition object is used to synchronize multiple threads waiting for the connection to
    # get into a specific state.
    _status_condition = None

    def __init__(self):
        self._connection_event_callbacks_lock = RLock()
        self._connection_event_callbacks = []

        self._lock = RLock()
        self._status_condition = Condition(self._lock)
        self._status = ClientStatus.INITIALIZED

    def get_status(self):
        with self._status_condition:
            return self._status

    def update_status(self, status):
        old_status = None
        new_status = None
        with self._status_condition:
            old_status = self._status
            new_status = status
            self._status = status
            self._status_condition.notify_all()

        # If the connection status has changed, fire the event.
        if old_status != new_status:
            self._fire_connection_event(new_status)

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

    # ------------------------------------------------------------------------------------------------
    # Event Handling
    # ------------------------------------------------------------------------------------------------
    def register_connection_event_callback(self, callback):
        with self._connection_event_callbacks_lock:
            if callback not in self._connection_event_callbacks:
                self._connection_event_callbacks.append(callback)
            else:
                l.debug("Callback was already registered.")

    def unregister_connection_event_callback(self, callback):
        with self._connection_event_callbacks_lock:
            if callback in self._connection_event_callbacks:
                self._connection_event_callbacks.remove(callback)
            else:
                l.debug("Callback was present: nothing to unregister.")

    def _fire_connection_event(self, connection_status):
        evt = ClientConnectionEvent(current_status=connection_status)
        for c in self._connection_event_callbacks:
            try:
                c(evt)
            except:
                l.exception("Unhandled error occurred while executing event handler")
