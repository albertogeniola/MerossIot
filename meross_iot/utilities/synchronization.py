from meross_iot.utilities.lock import lock_factory


class AtomicCounter(object):
    def __init__(self, initialValue):
        self._lock = lock_factory.build_rlock()
        self._val = initialValue

    def dec(self):
        with self._lock:
            self._val -= 1
            return self._val

    def inc(self):
        with self._lock:
            self._val += 1
            return self._val

    def get(self):
        with self._lock:
            return self._val