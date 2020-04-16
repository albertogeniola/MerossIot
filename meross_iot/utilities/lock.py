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
        self._lock_timeout_threshold = 5

    def configure_factory(self, enable_debug, lock_timeout_threshold):
        self._debug = enable_debug
        self._lock_timeout_threshold = lock_timeout_threshold

    def build_rlock(self):
        if self._debug:
            return ManagedRLock(lock_timeout_threshold=self._lock_timeout_threshold)
        else:
            return threading.RLock()


class LockMap(object):
    def __init__(self):
        self._lock_dict = {}
        self._lock = threading.RLock()

    def register_lock(self, lock_uuid):
        with self._lock:
            # { uuid: [lock_uuid, thread, count]}
            lock_data = self._lock_dict.get(lock_uuid, [lock_uuid, threading.current_thread(), 0])
            lock_data[2] += 1
            self._lock_dict[lock_uuid] = lock_data

    def unregister_lock(self, lock_uuid):
        with self._lock:
            # { uuid: [uuid, count]}
            lock_data = self._lock_dict.get(lock_uuid, None)
            if lock_data is None:
                raise Exception("ILLEGAL STATE")
            lock_data[2] -= 1
            if lock_data[2] == 0:
                del self._lock_dict[lock_uuid]
            else:
                self._lock_dict[lock_uuid] = lock_data

    def get_locking_thread_uuid(self, lock_uuid):
        with self._lock:
            return self._lock_dict.get(lock_uuid, [None, None, None])[1]


class ManagedRLock(object):
    def __init__(self, lock_timeout_threshold):
        # This is the guardina lock, used to synchronize access to this lock
        self._guad_lock = threading.RLock()

        self._lock_timeout_threshold = lock_timeout_threshold
        self._lock = threading.RLock()
        self._uuid = str(uuid4())

        try:
            self._is_owned = self._lock._is_owned
        except AttributeError:
            pass

    def acquire(self, blocking=True, timeout=-1):
        with self._guad_lock:
            result = self._lock.acquire(blocking=False)
            if not result and lockmap.get_locking_thread_uuid(self._uuid) is not None:
                l.warning("Possible DEADLOCK. Thread %s is trying to acquire lock %s, "
                          "which is already owned by thread %s." % (threading.current_thread().name, self._uuid,
                                                                    lockmap.get_locking_thread_uuid(self._uuid).name))
            elif result:
                self._lock.release()

        result = self._lock.acquire(blocking=blocking, timeout=timeout)
        if result:
            lockmap.register_lock(self._uuid)

        return result

    def release(self):
        with self._guad_lock:
            result = self._lock.release()
            lockmap.unregister_lock(self._uuid)
            return result

    def __enter__(self):
        return self.acquire()

    def __exit__(self, *args):
        return self.release()

    def __repr__(self):
        return "<ManagedRLock(%s)>" % self._uuid


# LockFactory Singleton
lock_factory = LockFactory()
lockmap = LockMap()


if __name__ == '__main__':
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    root.addHandler(handler)

    # Test with a deadlock
    l1 = ManagedRLock(lock_timeout_threshold=5)
    l2 = ManagedRLock(lock_timeout_threshold=5)

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
