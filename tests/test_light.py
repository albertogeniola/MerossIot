import concurrent
import os
from random import randint

from aiohttp import web
from aiohttp.test_utils import AioHTTPTestCase, unittest_run_loop

from meross_iot.controller.device import BaseDevice
from meross_iot.controller.mixins.light import LightMixin
from meross_iot.http_api import MerossHttpClient
from meross_iot.manager import MerossManager
from meross_iot.model.enums import OnlineStatus
from tests import async_get_client


if os.name == 'nt':
    import asyncio
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
else:
    import asyncio


class TestLight(AioHTTPTestCase):
    async def get_application(self):
        return web.Application()

    async def setUpAsync(self):
        # Wait some time before next test-burst
        await asyncio.sleep(10)
        self.meross_client, self.requires_logout = await async_get_client()

        # Look for a device to be used for this test
        self.meross_manager = MerossManager(http_client=self.meross_client)
        await self.meross_manager.async_init()
        devices = await self.meross_manager.async_device_discovery()
        self.light_devices = self.meross_manager.find_devices(device_class=LightMixin, online_status=OnlineStatus.ONLINE)

        # Update the states of all devices a first time
        concurrent_update = [d.async_update() for d in self.light_devices]
        await asyncio.gather(*concurrent_update)

    @unittest_run_loop
    async def test_rgb(self):
        # Make sure we have an RGB-capable available device
        rgb_capable = [d for d in self.light_devices if d.get_supports_rgb()]
        if len(rgb_capable) < 1:
            self.skipTest("Could not find any RGB-capable LightMixin within the given set of devices. "
                          "The test will be skipped")
        for light in rgb_capable:
            print(f"Testing device: {light.name}...")
            await light.async_update()

            # Set a random color
            r = randint(0, 256)
            g = randint(0, 256)
            b = randint(0, 256)
            await light.async_set_light_color(rgb=(r, g, b), onoff=True)

            # Check the color property returns red
            color = light.get_rgb_color()
            self.assertEqual(color, (r, g, b))

    @unittest_run_loop
    async def test_turn_on_off(self):
        # Make sure we have an RGB-capable available device
        rgb_capable = [d for d in self.light_devices if d.get_supports_rgb()]
        if len(rgb_capable) < 1:
            self.skipTest("Could not find any RGB-capable LightMixin within the given set of devices. "
                          "The test will be skipped")
        for light in rgb_capable:
            print(f"Testing device: {light.name}...")
            await light.async_update()

            # Turn device off
            await light.async_set_light_color(rgb=(255, 255, 255), onoff=False)
            await asyncio.sleep(1)
            # Make sure device is now off
            self.assertFalse(light.get_light_is_on())

            # Set a color and turn the device on
            await light.async_set_light_color(rgb=(0, 255, 0), onoff=True)
            await asyncio.sleep(1)
            # Make sure device is now on with that specific color set
            self.assertTrue(light.get_light_is_on())
            self.assertEqual(light.get_rgb_color(), (0, 255, 0))

            # Set a color without changing the on-off state
            await light.async_set_light_color(rgb=(255, 0, 0))
            await asyncio.sleep(1)
            # Make sure device is now showing the specific color
            self.assertTrue(light.get_light_is_on())
            self.assertEqual(light.get_rgb_color(), (255, 0, 0))

            # Turn off device without changing color
            await light.async_set_light_color(onoff=False)
            await asyncio.sleep(1)
            # Make sure device is now off
            self.assertFalse(light.get_light_is_on())

    @unittest_run_loop
    async def test_rgb_push_notification(self):
        # Make sure we have an RGB-capable available device
        rgb_capable = list(filter(lambda d: d.get_supports_rgb(), self.light_devices))
        if len(rgb_capable) < 1:
            self.skipTest("Could not find any RGB-capable LightMixin within the given set of devices. "
                          "The test will be skipped")

        light: BaseDevice = rgb_capable[0]
        print(f"Selected test device: {light.name}.")

        # Create a new manager
        new_meross_client, requires_logout = await async_get_client()
        m = None
        try:
            # Retrieve the same device with another manager
            m = MerossManager(http_client=new_meross_client)
            await m.async_init()
            await m.async_device_discovery()
            devs = m.find_devices(device_uuids=(light.uuid,))
            if len(devs) < 1:
                self.skipTest("Could not find dev for push notification")
                return
            dev = devs[0]

            # Set RGB color to known state
            r = await light.async_set_light_color(rgb=(255, 0, 0), onoff=True)
            await asyncio.sleep(2)

            # Turn on the device
            r = await light.async_set_light_color(rgb=(0, 255, 0), onoff=True)

            # Wait a bit and make sure the other manager received the push notification
            await asyncio.sleep(10)
            self.assertEqual(light.get_rgb_color(), (0, 255, 0))
            self.assertEqual(dev.get_rgb_color(), (0, 255, 0))
        finally:
            if m is not None:
                m.close()
            if requires_logout:
                await new_meross_client.async_logout()

    async def tearDownAsync(self):
        if self.requires_logout:
            await self.meross_client.async_logout()
        self.meross_manager.close()

        # Give a change to asyncio clean everything up
        await asyncio.sleep(1)
