import os

from aiohttp import web
from aiohttp.test_utils import AioHTTPTestCase, unittest_run_loop

from meross_iot.controller.mixins.spray import SprayMixin
from meross_iot.manager import MerossManager
from meross_iot.model.enums import OnlineStatus, SprayMode
from tests import async_get_client

if os.name == 'nt':
    import asyncio
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
else:
    import asyncio


class TestSpray(AioHTTPTestCase):
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
        self.test_devices = self.meross_manager.find_devices(device_class=SprayMixin, online_status=OnlineStatus.ONLINE)

    @unittest_run_loop
    async def test_spry(self):
        if len(self.test_devices) < 1:
            self.skipTest("Could not find any SprayMixin within the given set of devices. "
                          "The test will be skipped")

        dev = self.test_devices[0]
        print(f"Testing device {dev.name}")
        await dev.async_set_mode(mode=SprayMode.CONTINUOUS)
        self.assertEqual(dev.get_current_mode(), SprayMode.CONTINUOUS)

        await dev.async_set_mode(mode=SprayMode.INTERMITTENT)
        self.assertEqual(dev.get_current_mode(), SprayMode.INTERMITTENT)

        await dev.async_set_mode(mode=SprayMode.OFF)
        self.assertEqual(dev.get_current_mode(), SprayMode.OFF)

        await dev.async_update()

    async def tearDownAsync(self):
        if self.requires_logout:
            await self.meross_client.async_logout()
        self.meross_manager.close()

        # Give a change to asyncio clean everything up
        await asyncio.sleep(1)