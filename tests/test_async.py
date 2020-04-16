import os
import unittest
from logging import INFO
from meross_iot.logger import set_log_level
from meross_iot.manager import MerossManager
from meross_iot.utilities.synchronization import AtomicCounter



EMAIL = os.environ.get('MEROSS_EMAIL')
PASSWORD = os.environ.get('MEROSS_PASSWORD')


class TestMSS425ETest(unittest.TestCase):
    def setUp(self):
        self.counter = AtomicCounter(0)
        set_log_level(INFO, INFO)
        self.manager = MerossManager.from_email_and_password(meross_email=EMAIL, meross_password=PASSWORD)
        self.manager.start()

        # Retrieves the list of supported devices
        devices = self.manager.get_devices_by_type('mss425e')
        if len(devices) > 0:
            self.device = devices[0]
        else:
            self.skipTest("Could not find device mss425e")

    def print_result(self, error, res):
        # TODO: assertions
        print("Error: %s, Result: %s" % (error, res))
        print("Counter=%d" % self.counter.inc())

    # TODO: This fails. We need to investigate why.
    """
    def test_async(self):
        for i in range(0, 40):
            op = bool(random.getrandbits(1))
            channel = random.randrange(0, len(self.device.get_channels()))
            if not op:
                self.device.turn_off_channel(channel, callback=self.print_result)
            else:
                self.device.turn_on_channel(channel, callback=self.print_result)
        while self.counter.get() < 40:
            time.sleep(1)
    
    def test_sync(self):
        for i in range(0, 30):
            print("Executing command %d" % i)
            time.sleep(0.01)
            channel = random.randrange(0, len(self.device.get_channels()))
            self.device.turn_off_channel(channel)
            time.sleep(0.01)
            self.device.turn_on_channel(channel)
            time.sleep(0.01)
            print("Done command %d" % i)
    """

    def tearDown(self):
        self.manager.stop()
