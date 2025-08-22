import asyncio
import os
import logging

from aiohttp import web
from aiohttp.test_utils import AioHTTPTestCase, unittest_run_loop

from meross_iot.http_api import MerossHttpClient
from meross_iot.manager import MerossManager
from meross_iot.controller.device import BaseDevice
from meross_iot.controller.mixins.luminance import LuminanceMixin
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

class TestLuminance(AioHTTPTestCase):
    async def get_application(self):
        return web.Application()

    async def setUpAsync(self):
        self.meross_client, self.requires_logout = await async_get_client()

        # Look for a device to be used for this test
        self.meross_manager = MerossManager(http_client=self.meross_client)
        await self.meross_manager.async_init()
        devices = await self.meross_manager.async_device_discovery()
        self.luminance_devices = self.meross_manager.find_devices(device_class=LuminanceMixin, online_status=OnlineStatus.ONLINE)

        # Update the states of all devices a first time
        concurrent_update = [d.async_update() for d in self.luminance_devices]
        await asyncio.gather(*concurrent_update)

    async def set_luminance_and_sleep(self,dev, channel, luminance):
        print(f"Setting luminance - Channel {channel} to {luminance}")
        await dev.async_set_luminance(channel = channel,  luminance = luminance)
        await asyncio.sleep(5)
    
    async def tearDownAsync(self):
        if self.requires_logout:
            await self.meross_client.async_logout()
        self.meross_manager.close()

        # Give a change to asyncio clean everything up
        await asyncio.sleep(1)

    @unittest_run_loop
    async def test_set_luminance(self):
         # Try turning off the first object we find
        dev = self.luminance_devices[0]
        await self.set_luminance_and_sleep(dev,3,100)
        await self.set_luminance_and_sleep(dev,3,0)

    @unittest_run_loop
    async def test_bulk_set_luminance(self):
        dev = self.luminance_devices[0]

        print("Bulk setting luminance...")
        await dev.async_bulk_set_luminance({3:100,4:100,5:100})
        await asyncio.sleep(5)