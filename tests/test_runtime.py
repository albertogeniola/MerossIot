import os
from typing import List, Union

from aiohttp import web
from aiohttp.test_utils import AioHTTPTestCase, unittest_run_loop

from meross_iot.controller.device import BaseDevice
from meross_iot.controller.mixins.runtime import SystemRuntimeMixin
from meross_iot.manager import MerossManager
from meross_iot.model.enums import OnlineStatus
from tests import async_get_client

if os.name == 'nt':
    import asyncio

    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
else:
    import asyncio


class TestSystemRuntime(AioHTTPTestCase):
    async def get_application(self):
        return web.Application()

    async def setUpAsync(self):
        # Wait some time before next test-burst
        await asyncio.sleep(10)
        self.meross_client, self.requires_logout = await async_get_client()

        # Look for a device to be used for this test
        self.meross_manager = MerossManager(http_client=self.meross_client)
        await self.meross_manager.async_init()
        await self.meross_manager.async_device_discovery()
        self.test_devices: List[Union[BaseDevice, SystemRuntimeMixin]] = self.meross_manager.find_devices(device_class=SystemRuntimeMixin, online_status=OnlineStatus.ONLINE)

    @unittest_run_loop
    async def test_runtime_manual_update(self):
        if len(self.test_devices) < 1:
            self.skipTest("No device has been found to run this test.")
        for d in self.test_devices:
            info = await d.async_update_runtime_info()
            print(f"Wifi signal for device {d.name} is {info.get('signal')}%")
            self.assertEqual(d.cached_system_runtime_info, info)

    async def tearDownAsync(self):
        if self.requires_logout:
            await self.meross_client.async_logout()
        self.meross_manager.close()

        # Give a change to asyncio clean everything up
        await asyncio.sleep(1)
