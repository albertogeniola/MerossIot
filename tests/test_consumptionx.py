import os
from ctypes import Union
from typing import Optional

from aiohttp import web
from aiohttp.test_utils import AioHTTPTestCase, unittest_run_loop

from meross_iot.controller.device import BaseDevice
from meross_iot.controller.mixins.consumption import ConsumptionXMixin
from meross_iot.manager import MerossManager
from meross_iot.model.enums import OnlineStatus
from tests import async_get_client

# Fix event loop for Windows env
if os.name == 'nt':
    import asyncio
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
else:
    import asyncio


class TestConsumptionX(AioHTTPTestCase):
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
        toggle_devices = self.meross_manager.find_devices(device_class=ConsumptionXMixin, online_status=OnlineStatus.ONLINE)

        if len(toggle_devices) < 1:
            self.test_device = None
        else:
            self.test_device = toggle_devices[0]

    @unittest_run_loop
    async def test_consumptionx_local_state(self):
        if self.test_device is None:
            self.skipTest("No ConsumptionX device has been found to run this test on.")
        print(f"Testing device {self.test_device.name}")
        r = await self.test_device.async_get_daily_power_consumption()
        self.assertGreater(len(r), 1)

    async def tearDownAsync(self):
        if self.requires_logout:
            await self.meross_client.async_logout()
        self.meross_manager.close()

        # Give a change to asyncio clean everything up
        await asyncio.sleep(1)
