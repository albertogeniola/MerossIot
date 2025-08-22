import asyncio
import os
import logging

from aiohttp import web
from aiohttp.test_utils import AioHTTPTestCase, unittest_run_loop

from meross_iot.http_api import MerossHttpClient
from meross_iot.manager import MerossManager
from meross_iot.controller.device import BaseDevice
from meross_iot.controller.mixins.plantLight import PlantLightMixin
from meross_iot.http_api import MerossHttpClient
from meross_iot.manager import MerossManager
from meross_iot.model.enums import OnlineStatus
from tests import async_get_client


if os.name == 'nt':
    import asyncio
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
else:
    import asyncio

# logging.getLogger("meross_iot").setLevel(logging.DEBUG)

class TestPlantLight(AioHTTPTestCase):
    async def get_application(self):
        return web.Application()

    async def setUpAsync(self):
        self.meross_client, self.requires_logout = await async_get_client()

        # Look for a device to be used for this test
        self.meross_manager = MerossManager(http_client=self.meross_client)
        await self.meross_manager.async_init()
        devices = await self.meross_manager.async_device_discovery()
        self.plant_lights = self.meross_manager.find_devices(device_class=PlantLightMixin, online_status=OnlineStatus.ONLINE)

        # Update the states of all devices a first time
        concurrent_update = [d.async_update() for d in self.plant_lights]
        await asyncio.gather(*concurrent_update)
    
    async def tearDownAsync(self):
        if self.requires_logout:
            await self.meross_client.async_logout()
        self.meross_manager.close()

        # Give a change to asyncio clean everything up
        await asyncio.sleep(1)

    @unittest_run_loop
    async def test_onoff(self):
        dev = self.plant_lights[0]

        print(f"Turing off {dev.name} - Light A")
        await dev.async_turn_off(channel=1)
        await asyncio.sleep(1)

        print(f"Turning on {dev.name} - Light A")
        await dev.async_turn_on(channel=1)
        await asyncio.sleep(1)

        print(f"Turing off {dev.name} - Light B")
        await dev.async_turn_off(channel=2)
        await asyncio.sleep(1)

        print(f"Turning on {dev.name} - Light B")
        await dev.async_turn_on(channel=2)
        await asyncio.sleep(1)

        #dev.register_push_notification_handler_coroutine(light_coro)
        #while True:
        #    await asyncio.sleep(1)
        #return
        
    @unittest_run_loop
    async def test_set_color_and_luminance(self):
         # Try turning off the first object we find
        dev = self.plant_lights[0]
        rgbValue = (90,0,100)

        print("Setting color with luminance - Light A")
        await dev.async_set_light_color(channel = 1, rgb = rgbValue,luminance = 100)
        await asyncio.sleep(5)

        print("Getting color - Light A")
        rgb = dev.get_rgb_color(channel = 1)

        self.assertEqual(rgb,rgbValue)
        rgbValue2 = (90,0,100)

        print("Setting color - Light B")
        await dev.async_set_light_color(channel = 2, rgb = rgbValue, luminance = 100)
        await asyncio.sleep(5)

        print("Getting color - Light B")
        rgb = dev.get_rgb_color(channel = 2)

        self.assertEqual(rgb,rgbValue)

    @unittest_run_loop
    async def test_set_color_without_luminance(self):
         # Try turning off the first object we find
        dev = self.plant_lights[0]
        rgbValue = (90,0,100)
        desiredLuminance = 50
        print("Setting brightness - Light A")
        await dev.async_set_light_color(channel = 1, luminance = desiredLuminance)

        print("Setting color with luminance - Light A")
        await dev.async_set_light_color(channel = 1, rgb = rgbValue)
        await asyncio.sleep(5)

        print("Getting color - Light A")
        rgb = dev.get_rgb_color(channel = 1)

        self.assertEqual(rgb,rgbValue)
        self.assertEqual(desiredLuminance, dev.get_luminance(channel = 1))


    @unittest_run_loop
    async def test_set_brightness(self):
        dev = self.plant_lights[0]

        print("Getting color - Light A")
        rgb = dev.get_rgb_color(channel = 1)
        print(rgb)
        desiredLuminance = 50
        print("Setting brightness - Light A")
        await dev.async_set_light_color(channel = 1, luminance = desiredLuminance)
        await asyncio.sleep(5)

        print("Getting color - Light A")
        self.assertEqual(rgb, dev.get_rgb_color(channel = 1))
        self.assertEqual(desiredLuminance, dev.get_luminance(channel = 1))
