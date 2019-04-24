import os
import time
import unittest
import random

from meross_iot.api import MerossHttpClient

EMAIL = os.environ.get('MEROSS_EMAIL')
PASSWORD = os.environ.get('MEROSS_PASSWORD')


class TestHttpMethods(unittest.TestCase):
    def setUp(self):
        self.client = MerossHttpClient(email=EMAIL, password=PASSWORD)

    def test_device_listing(self):
        devices = self.client.list_devices()
        assert devices is not None
        assert len(devices) > 0

    def test_supported_device_listing(self):
        devices = self.client.list_supported_devices()
        assert devices is not None
        assert len(devices) > 0


class TestMSL120Test(unittest.TestCase):
    def setUp(self):
        httpHandler = MerossHttpClient(email=EMAIL, password=PASSWORD)

        # Retrieves the list of supported devices
        devices = httpHandler.list_supported_devices()
        for counter, device in enumerate(devices):
            if device._type == 'msl120':
                self.device = device
                break

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
