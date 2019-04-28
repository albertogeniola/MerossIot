import os
import time
import unittest
from meross_iot.manager import MerossManager
from threading import Thread, current_thread
import random
from meross_iot.logger import set_log_level
from logging import DEBUG, INFO


EMAIL = os.environ.get('MEROSS_EMAIL')
PASSWORD = os.environ.get('MEROSS_PASSWORD')


class TestMSS425ETest(unittest.TestCase):
    def setUp(self):
        set_log_level(DEBUG, DEBUG)
        self.manager = MerossManager(meross_email=EMAIL, meross_password=PASSWORD)
        self.manager.start()

        # Retrieves the list of supported devices
        devices = self.manager.get_devices_by_type('mss425e')
        if len(devices) > 0:
            self.device = devices[0]
        else:
            raise Exception("Could not find device mss425e")

    def test_multithreading(self):
        def thread_run():
            wait_time = random.random() * 3
            op = bool(random.getrandbits(1))
            time.sleep(wait_time)
            print("Thread %s executing..." % current_thread().name)
            channel = random.randrange(0, len(self.device.get_channels()))
            if not op:
                self.device.turn_off_channel(channel)
            else:
                self.device.turn_on_channel(channel)

            print("Thread %s done." % current_thread().name)

        threads = []
        for i in range(0, 10):
            t = Thread(target=thread_run)
            threads.append(t)

        for t in threads:
            t.start()

        for t in threads:
            t.join(20)
            if t.isAlive():
                raise Exception("Test not passed.")

    def test_seq_commands(self):
        for i in range(0, 30):
            time.sleep(0.01)
            channel = random.randrange(0, len(self.device.get_channels()))
            self.device.turn_off_channel(channel)
            time.sleep(0.01)
            self.device.turn_on_channel(channel)
            time.sleep(0.01)

    def tearDown(self):
        self.manager.stop()
