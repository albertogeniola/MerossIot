import os
from random import randint
import asyncio
from aiohttp import web
from aiohttp.test_utils import AioHTTPTestCase, unittest_run_loop

from meross_iot.controller.mixins.light import LightMixin
from meross_iot.http_api import MerossHttpClient
from meross_iot.manager import MerossManager
from meross_iot.model.enums import OnlineStatus

EMAIL = os.environ.get('MEROSS_EMAIL')
PASSWORD = os.environ.get('MEROSS_PASSWORD')


if os.name == 'nt':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


class TestLight(AioHTTPTestCase):
    async def get_application(self):
        return web.Application()

    async def setUpAsync(self):
        self.meross_client = await MerossHttpClient.async_from_user_password(email=EMAIL, password=PASSWORD)

        # Look for a device to be used for this test
        manager = MerossManager(http_client=self.meross_client)
        await manager.async_init()
        devices = await manager.async_device_discovery()
        self.light_devices = manager.find_devices(device_class=LightMixin, online_status=OnlineStatus.ONLINE)

        # Update the states of all devices a first time
        concurrent_update = [d.async_update() for d in self.light_devices]
        await asyncio.gather(*concurrent_update)

    @unittest_run_loop
    async def test_rgb(self):
        # Make sure we have an RGB-capable available device
        rgb_capable = list(filter(lambda d: d.get_supports_rgb(), self.light_devices))
        if len(rgb_capable) < 1:
            self.skipTest("Could not find any RGB-capable LightMixin within the given set of devices. "
                          "The test will be skipped")
            return

        for light in rgb_capable:
            await light.async_update()

            # Set a random color
            r = randint(0, 256)
            g = randint(0, 256)
            b = randint(0, 256)
            await light.async_set_light_color(rgb=(r, g, b))

            # Check the color property returns red
            color = light.get_rgb_color()
            self.assertEqual(color, (r, g, b))

    @unittest_run_loop
    async def test_rgb_push_notification(self):
        # Make sure we have an RGB-capable available device
        rgb_capable = list(filter(lambda d: d.get_supports_rgb(), self.light_devices))
        if len(rgb_capable) < 1:
            self.skipTest("Could not find any RGB-capable LightMixin within the given set of devices. "
                          "The test will be skipped")
            return

        light = rgb_capable[0]

        # Create a new manager
        new_meross_client = await MerossHttpClient.async_from_user_password(email=EMAIL, password=PASSWORD)
        m = None
        try:
            # Retrieve the same device with another manager
            m = MerossManager(http_client=new_meross_client)
            await m.async_init()
            await m.async_device_discovery()
            devs = m.find_devices(device_uuids=(light.uuid,))
            dev = devs[0]

            # Set RGB color to known state
            r = await light.async_set_light_color(rgb=(255, 0, 0))
            await asyncio.sleep(2)

            # Turn on the device
            r = await light.async_set_light_color(rgb=(0, 255, 0))

            # Wait a bit and make sure the other manager received the push notification
            await asyncio.sleep(10)
            self.assertEqual(light.get_rgb_color(), (0, 255, 0))
            self.assertEqual(dev.get_rgb_color(), (0, 255, 0))
        finally:
            if m is not None:
                m.close()
            await new_meross_client.async_logout()

    async def tearDownAsync(self):
        await self.meross_client.async_logout()
