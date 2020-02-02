import os
import random
import time
import unittest

from meross_iot.cloud.devices.humidifier import SprayMode
from meross_iot.manager import MerossManager

EMAIL = os.environ.get('MEROSS_EMAIL')
PASSWORD = os.environ.get('MEROSS_PASSWORD')


class TestMSX0Test(unittest.TestCase):
    def setUp(self):
        self.manager = MerossManager(meross_email=EMAIL, meross_password=PASSWORD)
        self.manager.start()

        # Retrieves the list of supported devices
        devices = self.manager.get_devices_by_type('msxh0')
        if len(devices) > 0:
            self.device = devices[0]
        else:
            raise Exception("Could not find device msxh0")

    def test_spray_mode(self):
        time.sleep(2)
        self.device.set_spray_mode(SprayMode.CONTINUOUS)
        time.sleep(2)
        self.assertEqual(self.device.get_spray_mode(), SprayMode.CONTINUOUS)

        time.sleep(2)
        self.device.set_spray_mode(SprayMode.INTERMITTENT)
        time.sleep(2)
        self.assertEqual(self.device.get_spray_mode(), SprayMode.INTERMITTENT)

        time.sleep(2)
        self.device.set_spray_mode(SprayMode.OFF)
        time.sleep(2)
        self.assertEqual(self.device.get_spray_mode(), SprayMode.OFF)

    def test_get_info(self):
        state = self.device.get_status()
        assert state is not None

    def test_set_light_color(self):
        r = int(random.random() * 255)
        g = int(random.random() * 255)
        b = int(random.random() * 255)
        self.device.configure_light(onoff=1, rgb=(r, g, b), luminance=100)
        time.sleep(5)
        light_state = self.device.get_light_color()
        self.assertEqual(light_state, (r, g, b))

    def tearDown(self):
        self.manager.stop()
