import os

from aiohttp import web
from aiohttp.test_utils import AioHTTPTestCase, unittest_run_loop

from meross_iot.controller.device import BaseDevice
from meross_iot.controller.mixins.system import SystemAllMixin
from meross_iot.manager import MerossManager
from meross_iot.model.enums import OnlineStatus
from meross_iot.model.exception import CommandTimeoutError
from tests import async_get_client

if os.name == 'nt':
    import asyncio
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
else:
    import asyncio


class TestTimeout(AioHTTPTestCase):
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
        self.test_devices = self.meross_manager.find_devices(device_class=SystemAllMixin,
                                                             online_status=OnlineStatus.ONLINE)

    @unittest_run_loop
    async def test_short_timeout(self):
        if len(self.test_devices) < 1:
            self.skipTest("No device has been found to run this test.")

        # Select a device
        device: BaseDevice = self.test_devices[0]
        print(f"Selected device {device} for testing.")
        print(f"Default timeout was: {device.default_command_timeout}s.")

        # Set a very low timeout to trigger a command timeout error
        device.default_command_timeout = 0.01
        print(f"New timeout: {device.default_command_timeout}s.")

        # This should trigger a timeout error
        with self.assertRaises(CommandTimeoutError):
            await device.async_update()

    async def tearDownAsync(self):
        if self.requires_logout:
            await self.meross_client.async_logout()
        self.meross_manager.close()

        # Give a change to asyncio clean everything up
        await asyncio.sleep(1)