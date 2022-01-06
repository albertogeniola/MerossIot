import os

from aiohttp import web
from aiohttp.test_utils import AioHTTPTestCase, unittest_run_loop

from meross_iot.controller.subdevice import Ms100Sensor
from meross_iot.manager import MerossManager
from meross_iot.model.enums import OnlineStatus
from meross_iot.model.plugin.hub import BatteryInfo
from tests import async_get_client


if os.name == 'nt':
    import asyncio
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
else:
    import asyncio


class TestSensor(AioHTTPTestCase):
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
        self.test_devices = self.meross_manager.find_devices(device_class=Ms100Sensor, online_status=OnlineStatus.ONLINE)

    @unittest_run_loop
    async def test_temperature(self):
        if len(self.test_devices) < 1:
            self.skipTest("No sensor device has been found to run this test.")

        dev = self.test_devices[0]
        print(f"Testing device {dev.name}")
        await dev.async_update()

        self.assertIsNotNone(dev.last_sampled_temperature)
        self.assertIsNotNone(dev.last_sampled_time)

    @unittest_run_loop
    async def test_battery(self):
        if len(self.test_devices) < 1:
            self.skipTest("No sensor device has been found to run this test.")

        dev = self.test_devices[0]
        print(f"Testing device {dev.name}")
        await dev.async_update()
        res = await dev.async_get_battery_life()

        self.assertIsInstance(res, BatteryInfo)
        self.assertGreater(res.remaining_charge, 0)

    async def tearDownAsync(self):
        if self.requires_logout:
            await self.meross_client.async_logout()
        self.meross_manager.close()

        # Give a change to asyncio clean everything up
        await asyncio.sleep(1)