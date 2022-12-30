import os
import random
from random import randint
from typing import Union

from aiohttp import web
from aiohttp.test_utils import AioHTTPTestCase, unittest_run_loop

from meross_iot.controller.device import BaseDevice
from meross_iot.controller.mixins.diffuser_light import DiffuserLightMixin
from meross_iot.controller.mixins.diffuser_spray import DiffuserSprayMixin
from meross_iot.manager import MerossManager
from meross_iot.model.enums import OnlineStatus, DiffuserLightMode, DiffuserSprayMode
from tests import async_get_client

if os.name == 'nt':
    import asyncio
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
else:
    import asyncio


class TestDiffuser(AioHTTPTestCase):
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
        self.light_devices = self.meross_manager.find_devices(device_class=DiffuserLightMixin, online_status=OnlineStatus.ONLINE)
        self.spray_devices = self.meross_manager.find_devices(device_class=DiffuserSprayMixin, online_status=OnlineStatus.ONLINE)


    @unittest_run_loop
    async def test_light_rgb(self):
        if len(self.light_devices) < 1:
            self.skipTest("Could not find any DiffuserLightMixin within the given set of devices. "
                          "The test will be skipped.")
        for light in self.light_devices:
            print(f"Testing device: {light.name}...")
            await light.async_update()

            await light.async_set_light_mode(mode=DiffuserLightMode.FIXED_RGB)

            # Set a random color
            r = randint(0, 256)
            g = randint(0, 256)
            b = randint(0, 256)
            await light.async_set_light_mode(rgb=(r, g, b), onoff=True)

            # Check the color property returns red
            color = light.get_light_rgb_color()
            self.assertEqual(color, (r, g, b))

    @unittest_run_loop
    async def test_turn_light_on_off(self):
        if len(self.light_devices) < 1:
            self.skipTest("Could not find any DiffuserLightMixin within the given set of devices. "
                          "The test will be skipped.")
        for light in self.light_devices:
            print(f"Testing device: {light.name}...")
            await light.async_update()  # type: Union[BaseDevice, DiffuserLightMode]

            # Set mode to FIXED RGB
            await light.async_set_light_mode(mode=DiffuserLightMode.FIXED_RGB)

            # Turn device off
            await light.async_set_light_mode(onoff=False)
            self.assertFalse(light.get_light_is_on())
            # Change the color without turning it on
            await light.async_set_light_mode(rgb=(255, 0, 0))
            # Make sure device is now showing the specific color
            self.assertEqual(light.get_light_rgb_color(), (255, 0, 0))
            self.assertFalse(light.get_light_is_on())
            # Turn device on and check if the color is right
            await light.async_set_light_mode(onoff=True)
            self.assertTrue(light.get_light_is_on())

            # Turn off device without changing color
            await light.async_set_light_mode(onoff=False)
            await asyncio.sleep(1)
            # Make sure device is now off
            self.assertFalse(light.get_light_is_on())

    @unittest_run_loop
    async def test_light_mode(self):
        if len(self.light_devices) < 1:
            self.skipTest("Could not find any DiffuserLightMixin within the given set of devices. "
                          "The test will be skipped.")
        for light in self.light_devices:
            print(f"Testing device: {light.name}...")
            await light.async_update()

            await light.async_set_light_mode(mode=DiffuserLightMode.FIXED_LUMINANCE, onoff=True)
            self.assertEqual(light.get_light_mode(), DiffuserLightMode.FIXED_LUMINANCE)
            await light.async_set_light_mode(mode=DiffuserLightMode.ROTATING_COLORS)
            self.assertEqual(light.get_light_mode(), DiffuserLightMode.ROTATING_COLORS)
            await light.async_set_light_mode(mode=DiffuserLightMode.FIXED_RGB)
            self.assertEqual(light.get_light_mode(), DiffuserLightMode.FIXED_RGB)

    @unittest_run_loop
    async def test_light_brightness(self):
        if len(self.light_devices) < 1:
            self.skipTest("Could not find any DiffuserLightMixin within the given set of devices. "
                          "The test will be skipped.")
        for light in self.light_devices:
            print(f"Testing device: {light.name}...")
            await light.async_update()

            await light.async_set_light_mode(onoff=True)
            for i in range(0,100,10):
                await light.async_set_light_mode(brightness=i)
                await asyncio.sleep(0.5)
                self.assertEqual(light.get_light_brightness(), i)

    @unittest_run_loop
    async def test_spray_mode(self):
        if len(self.spray_devices) < 1:
            self.skipTest("Could not find any DiffuserSprayMixin within the given set of devices. "
                          "The test will be skipped.")
        for spray in self.spray_devices:  # type: Union[BaseDevice, DiffuserSprayMixin]
            print(f"Testing device: {spray.name}...")
            await spray.async_update()

            await asyncio.sleep(1)
            await spray.async_set_spray_mode(DiffuserSprayMode.LIGHT)
            self.assertEqual(spray.get_current_spray_mode(), DiffuserSprayMode.LIGHT)
            await asyncio.sleep(1)
            await spray.async_set_spray_mode(DiffuserSprayMode.STRONG)
            self.assertEqual(spray.get_current_spray_mode(), DiffuserSprayMode.STRONG)
            await asyncio.sleep(1)
            await spray.async_set_spray_mode(DiffuserSprayMode.OFF)
            self.assertEqual(spray.get_current_spray_mode(), DiffuserSprayMode.OFF)

    async def tearDownAsync(self):
        if self.requires_logout:
            await self.meross_client.async_logout()
        self.meross_manager.close()

        # Give a change to asyncio clean everything up
        await asyncio.sleep(1)
