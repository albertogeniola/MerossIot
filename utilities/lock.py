import os
import threading
import time
import logging
import sys, traceback
from uuid import uuid4

l = logging.getLogger(__name__)


class LockFactory(object):
    def __init__(self, enable_debug=False):
        self._debug = enable_debug
        self._lock_timeout = 9

    def configure_factory(self, enabled_debug, lock_timeout):
        self._debug = enabled_debug
        self._lock_timeout = lock_timeout

    def build_rlock(self):
        if self._debug:
            return ManagedRLock(default_timeout=self._lock_timeout)
        else:
            return threading.RLock()


class ManagedRLock(object):
    def __init__(self, default_timeout=None):
        # Lock used to monitor access to this managed lock
        self._gatelock = threading.RLock()

        # Managed lock instance
        self._timeout = default_timeout
        self._lock = threading.RLock()
        self._lock_id = uuid4()
        self._owner = None

    def acquire(self, blocking=True, timeout=-1):
        with self._gatelock:
            l.debug("Thread %s acquiring lock %s" % (threading.current_thread().name, self._lock_id))
            to = timeout
            if to == -1:
                to = self._timeout
            result = self._lock.acquire(blocking=blocking, timeout=to)
            if not result:
                traceback.extract_stack()
                # This is probably a deadlock
                stack = traceback.format_stack()
                l.error("XXX POSSIBLE DEADLOCK XXX: Thread %s failed to acquire lock %s. "
                            "The owner thread is %s. \nCallStack:\n%s" %
                            (threading.current_thread().name, self._lock_id, self._owner.name,
                             "".join(stack)))
            else:
                self._owner = threading.current_thread()
            return result

    def release(self):
        with self._gatelock:
            if self._owner is not None:
                self._lock.release()
                self._owner = None

    def __enter__(self):
        with self._gatelock:
            return self.acquire()

    def __exit__(self, exc_type, exc_val, exc_tb):
        with self._gatelock:
            self.release()


# LockFactory Singleton
lock_factory = LockFactory()


if __name__ == '__main__':
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    root.addHandler(handler)

    # Test with a deadlock
    l1 = ManagedRLock()
    l2 = ManagedRLock()

    def deadlocker(l1, l2):
        with l1:
            with l2:
                print("Lock acquired.")
                time.sleep(120)

    t1 = threading.Thread(target=deadlocker, args=(l1,l2))
    t2 = threading.Thread(target=deadlocker, args=(l2, l1))
    t1.start()
    t2.start()
    t2.join()
    t1.join()
