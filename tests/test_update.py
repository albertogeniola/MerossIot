import os

from aiohttp import web
from aiohttp.test_utils import AioHTTPTestCase, unittest_run_loop

from meross_iot.controller.mixins.light import LightMixin
from meross_iot.controller.mixins.system import SystemAllMixin
from meross_iot.controller.mixins.toggle import ToggleXMixin
from meross_iot.manager import MerossManager
from meross_iot.model.enums import OnlineStatus
from tests import async_get_client


if os.name == 'nt':
    import asyncio
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
else:
    import asyncio


class TestUpdate(AioHTTPTestCase):
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
    async def test_update(self):
        if len(self.test_devices) < 1:
            self.skipTest("No device has been found to run this test UPDATE ALL on it.")
            return

        # Turn off device to start from a clean state
        for d in self.test_devices:
            if isinstance(d, LightMixin):
                self.assertIsNone(d.get_rgb_color())
            elif isinstance(d, ToggleXMixin):
                self.assertIsNone(d.is_on())
            await d.async_update()

            if isinstance(d, LightMixin):
                self.assertIsNotNone(d.get_rgb_color())
            elif isinstance(d, ToggleXMixin):
                self.assertIsNotNone(d.is_on())

    async def tearDownAsync(self):
        if self.requires_logout:
            await self.meross_client.async_logout()
