import os
from aiohttp import web
from aiohttp.test_utils import AioHTTPTestCase, unittest_run_loop

from meross_iot.controller.mixins.garage import GarageOpenerMixin
from meross_iot.manager import MerossManager
from meross_iot.model.enums import OnlineStatus
from tests import async_get_client


if os.name == 'nt':
    import asyncio

    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
else:
    import asyncio


class TestGarageOpener(AioHTTPTestCase):
    async def get_application(self):
        return web.Application()

    async def setUpAsync(self):
        # Wait some time before next test-burst
        await asyncio.sleep(10)
        self.meross_client, self.requires_logout = await async_get_client()

        # Look for a device to be used for this test
        manager = MerossManager(http_client=self.meross_client)
        await manager.async_init()
        devices = await manager.async_device_discovery()
        self.garage_devices = manager.find_devices(device_class=GarageOpenerMixin, online_status=OnlineStatus.ONLINE)

    @unittest_run_loop
    async def test_open_close(self):
        if len(self.garage_devices) < 1:
            self.skipTest("Could not find any Garage Opener within the given set of devices. "
                          "The test will be skipped")
            return

        garage = self.garage_devices[0]

        # Without a full update, the status will be NONE
        current_status = garage.get_is_open(channel=0)
        self.assertIsNone(current_status)

        # Trigger the full update
        await garage.async_update()
        self.assertIsNotNone(garage.get_is_open())

        # Toggle
        is_open = garage.get_is_open()
        if is_open:
            await garage.async_close()
        else:
            await garage.async_open()
        await asyncio.sleep(30)
        self.assertEqual(garage.get_is_open(), not is_open)

        is_open = garage.get_is_open()
        if is_open:
            await garage.async_close()
        else:
            await garage.async_open()
        await asyncio.sleep(30)
        self.assertEqual(garage.get_is_open(), not is_open)

    async def tearDownAsync(self):
        if self.requires_logout:
            await self.meross_client.async_logout()
