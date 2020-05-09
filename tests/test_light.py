import os
from random import randint

from aiohttp import web
from aiohttp.test_utils import AioHTTPTestCase, unittest_run_loop

from meross_iot.controller.mixins.light import LightMixin
from meross_iot.http_api import MerossHttpClient
from meross_iot.manager import MerossManager
from meross_iot.model.enums import OnlineStatus

EMAIL = os.environ.get('MEROSS_EMAIL')
PASSWORD = os.environ.get('MEROSS_PASSWORD')


class TestToggleX(AioHTTPTestCase):
    async def get_application(self):
        return web.Application()

    async def setUpAsync(self):
        self.meross_client = await MerossHttpClient.async_from_user_password(email=EMAIL, password=PASSWORD)

        # Look for a device to be used for this test
        manager = MerossManager(http_client=self.meross_client)
        await manager.async_init()
        devices = await manager.async_device_discovery()
        self.light_devices = manager.find_device(device_class=LightMixin, online_status=OnlineStatus.ONLINE)

    @unittest_run_loop
    async def test_rgb(self):
        # Make sure we have an RGB-capable available device
        rgb_capable = list(filter(lambda d: d.supports_rgb,self.light_devices))
        if len(rgb_capable) < 1:
            self.skipTest("Could not find any RGB-capable LightMixin within the given set of devices. "
                          "The test will be skipped")
            return

        light = rgb_capable[0]

        # Set a random color
        r = randint(0, 256)
        g = randint(0, 256)
        b = randint(0, 256)
        await light.async_set_light_color(rgb=(r, g, b))

        # Check the color property returns red
        color = light.rgb_color
        self.assertEqual(color, (r, g, b))

    """
    async def test_toggle_push_notification(self):
        if self.test_device is None:
            self.skipTest("No ToggleX device has been found to run this test on.")
            return

        # Create a new manager
        new_meross_client = await MerossHttpClient.async_from_user_password(email=EMAIL, password=PASSWORD)
        m = None
        try:
            # Retrieve the same device with another manager
            m = MerossManager(http_client=new_meross_client)
            await m.async_device_discovery()
            devs = m.find_device(uuids=(self.test_device.uuid))
            dev = devs[0]

            # Turn off device to start from a clean state
            r = await self.test_device.turn_off()
            await asyncio.sleep(2)

            # Turn on the device
            r = await self.test_device.turn_on()
            # Wait a bit and make sure the other manager received the push notification
            await asyncio.sleep(2)
            self.assertTrue(self.test_device.is_on)
            self.assertTrue(dev.is_on)

            # Turn off the device
            await asyncio.sleep(1)
            r = await self.test_device.turn_off()
            # Wait a bit and make sure the other manager received the push notification
            await asyncio.sleep(2)
            self.assertFalse(self.test_device.is_on)
            self.assertFalse(dev.is_on)

        finally:
            if m is not None:
                m.close()
            await new_meross_client.async_logout()
    """

    async def tearDownAsync(self):
        await self.meross_client.async_logout()
