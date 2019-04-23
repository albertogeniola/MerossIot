from threading import RLock


class AtomicCounter(object):
    _lock = None

    def __init__(self, initialValue):
        self._lock = RLock()
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