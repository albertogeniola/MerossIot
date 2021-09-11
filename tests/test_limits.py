import os
from datetime import timedelta
from typing import List

from aiohttp import web
from aiohttp.test_utils import AioHTTPTestCase, unittest_run_loop
from meross_iot.utilities.limiter import RateLimitChecker

from meross_iot.controller.mixins.electricity import ElectricityMixin
from meross_iot.manager import MerossManager
from meross_iot.model.enums import OnlineStatus
from meross_iot.model.exception import RateLimitExceeded
from tests import async_get_client

if os.name == 'nt':
    import asyncio
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
else:
    import asyncio


BURST_RATE = 5


class TestLimits(AioHTTPTestCase):
    test_sensors: List[ElectricityMixin]

    async def get_application(self):
        return web.Application()

    async def setUpAsync(self):
        # Wait some time before next test-burst
        await asyncio.sleep(10)
        self.meross_client, self.requires_logout = await async_get_client()

        # Look for a device to be used for this test
        rate_limiter = RateLimitChecker(global_time_window=timedelta(seconds=1), global_burst_rate=BURST_RATE, device_max_command_queue=BURST_RATE)
        manager = MerossManager(http_client=self.meross_client, rate_limiter=rate_limiter)
        await manager.async_init()
        devices = await manager.async_device_discovery()

        self.test_sensors = manager.find_devices(device_class=ElectricityMixin, online_status=OnlineStatus.ONLINE)

    async def _perform_requests(self, sensor: ElectricityMixin, n_requests: int):
        tasks = []
        for i in range(n_requests):
            tasks.append(sensor.async_get_instant_metrics())
        await asyncio.gather(*tasks)

    @unittest_run_loop
    async def test_sustainable_rate(self):
        if len(self.test_sensors) < 1:
            self.skipTest("No device found for this test")

        await self._perform_requests(sensor=self.test_sensors[0], n_requests=BURST_RATE-1)

    @unittest_run_loop
    async def test_unsustainable_rate(self):
        if len(self.test_sensors) < 1:
            self.skipTest("No device found for this test")

        with self.assertRaises(RateLimitExceeded):
            await self._perform_requests(sensor=self.test_sensors[0], n_requests=50)

    async def tearDownAsync(self):
        if self.requires_logout:
            await self.meross_client.async_logout()
