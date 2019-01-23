import os
import time
import unittest

from meross_iot.api import MerossHttpClient
from meross_iot.supported_devices.power_plugs import Mss310

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


class TestMSS310Test(unittest.TestCase):
    def setUp(self):
        httpHandler = MerossHttpClient(email=EMAIL, password=PASSWORD)

        # Retrieves the list of supported devices
        devices = httpHandler.list_supported_devices()
        for counter, device in enumerate(devices):
            if isinstance(device, Mss310):
                self.device = device
                break

    def test_power_cycle(self):
        self.device.turn_on()
        time.sleep(2)
        self.assertTrue(self.device.get_status())

        self.device.turn_off()
        time.sleep(2)
        self.assertFalse(self.device.get_status())

        self.device.turn_on()
        time.sleep(2)

        self.assertTrue(self.device.get_status())

    def test_get_info(self):
        consumption = self.device.get_power_consumptionX()
        assert consumption is not None

        wifi_list = self.device.get_wifi_list()
        assert wifi_list is not None

        trace = self.device.get_trace()
        assert trace is not None

        debug = self.device.get_debug()
        assert debug is not None

        abilities = self.device.get_abilities()
        assert abilities is not None

        electricity = self.device.get_electricity()
        assert electricity is not None
