import os
import unittest

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
        devices = self.client.list_devices()
        assert devices is not None
        assert len(devices) > 0
