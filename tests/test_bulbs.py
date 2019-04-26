from meross_iot.manager import MerossManager
import os
import time
import unittest
import random


EMAIL = os.environ.get('MEROSS_EMAIL')
PASSWORD = os.environ.get('MEROSS_PASSWORD')


class TestMSL120Test(unittest.TestCase):
    def setUp(self):
        self.manager = MerossManager(meross_email=EMAIL, meross_password=PASSWORD)
        self.manager.start()

        # Retrieves the list of supported devices
        devices = self.manager.get_devices_by_type('msl120')
        if len(devices) > 0:
            self.device = devices[0]
        else:
            raise Exception("Could not find device msl120")

    def test_power_cycle(self):
        self.device.turn_on()
        time.sleep(2)
        self.assertTrue(self.device.get_status()['on'])

        self.device.turn_off()
        time.sleep(2)
        self.assertFalse(self.device.get_status()['on'])

        self.device.turn_on()
        time.sleep(2)

        self.assertTrue(self.device.get_status()['on'])

    def test_get_info(self):
        state = self.device.get_status()
        assert state is not None

    def test_set_light_color(self):
        r = int(random.random() * 255)
        g = int(random.random() * 255)
        b = int(random.random() * 255)
        self.device.set_light_color(channel=0, rgb=(r, g, b))
        time.sleep(5)
        bulb_state = self.device.get_light_color(channel=0)
        # TODO: RGB state is somehow normalized on the server side. We need to investigate the logic behind that...

    def tearDown(self):
        self.device.turn_off()
        self.manager.stop()
