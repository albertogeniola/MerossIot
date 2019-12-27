import os
import time
import unittest

from meross_iot.manager import MerossManager

EMAIL = os.environ.get('MEROSS_EMAIL')
PASSWORD = os.environ.get('MEROSS_PASSWORD')


class TestMSS210Test(unittest.TestCase):
    def setUp(self):
        self.manager = MerossManager(meross_email=EMAIL, meross_password=PASSWORD)
        self.manager.start()

        # Retrieves the list of supported devices
        devices = self.manager.get_devices_by_type('mss210')
        if len(devices) > 0:
            self.device = devices[0]
        else:
            raise Exception("Could not find device ms210")

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
        state = self.device.get_status()
        assert state is not None

        wifi_list = self.device.get_wifi_list()
        assert wifi_list is not None

        trace = self.device.get_trace()
        assert trace is not None

        debug = self.device.get_debug()
        assert debug is not None

    def tearDown(self):
        self.manager.stop()


class TestMSS310Test(unittest.TestCase):
    def setUp(self):
        self.manager = MerossManager(meross_email=EMAIL, meross_password=PASSWORD)
        self.manager.start()

        # Retrieves the list of supported devices
        devices = self.manager.get_devices_by_type('mss310')
        if len(devices) > 0:
            self.device = devices[0]
        else:
            raise Exception("Could not find device mss310")

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
        consumption = self.device.get_power_consumption()
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

    def tearDown(self):
        self.manager.stop()


class TestMSS425ETest(unittest.TestCase):
    def setUp(self):
        self.manager = MerossManager(meross_email=EMAIL, meross_password=PASSWORD)
        self.manager.start()

        # Retrieves the list of supported devices
        devices = self.manager.get_devices_by_type('mss425e')
        if len(devices) > 0:
            self.device = devices[0]
        else:
            raise Exception("Could not find device mss425e")

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

    def test_usb(self):
        self.device.enable_usb()
        time.sleep(2)
        self.assertTrue(self.device.get_usb_status())

        self.device.enable_usb()
        time.sleep(2)
        self.assertTrue(self.device.get_usb_status())

    def test_channels(self):
        self.device.turn_off()
        time.sleep(2)
        self.assertFalse(self.device.get_status())

        # Test each channel one by one
        for c in self.device.get_channels():
            self.device.turn_on_channel(c)
            time.sleep(2)
            self.assertTrue(self.device.get_channel_status(c))

            time.sleep(2)
            self.device.turn_off_channel(c)
            time.sleep(2)
            self.assertFalse(self.device.get_channel_status(c))

    def test_get_info(self):
        state = self.device.get_status()
        assert state is not None

        wifi_list = self.device.get_wifi_list()
        assert wifi_list is not None

        trace = self.device.get_trace()
        assert trace is not None

        debug = self.device.get_debug()
        assert debug is not None

    def tearDown(self):
        self.manager.stop()


class TestMSS530HTest(unittest.TestCase):
    def setUp(self):
        self.manager = MerossManager(meross_email=EMAIL, meross_password=PASSWORD)
        self.manager.start()

        # Retrieves the list of supported devices
        devices = self.manager.get_devices_by_type('mss530h')
        if len(devices) > 0:
            self.device = devices[0]
        else:
            raise Exception("Could not find device mss530h")

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

        self.device.turn_off()
        time.sleep(2)
        self.assertFalse(self.device.get_status())

    def test_get_info(self):
        state = self.device.get_status()
        assert state is not None

        wifi_list = self.device.get_wifi_list()
        assert wifi_list is not None

        trace = self.device.get_trace()
        assert trace is not None

        debug = self.device.get_debug()
        assert debug is not None

    def tearDown(self):
        self.manager.stop()
