import os
from random import randint
import asyncio
from typing import List, Any

from aiohttp import web
from aiohttp.test_utils import AioHTTPTestCase, unittest_run_loop

from meross_iot.controller.mixins.electricity import ElectricityMixin
from meross_iot.controller.mixins.light import LightMixin
from meross_iot.http_api import MerossHttpClient
from meross_iot.manager import MerossManager
from meross_iot.model.enums import OnlineStatus
from meross_iot.model.exception import RateLimitExceeded

EMAIL = os.environ.get('MEROSS_EMAIL')
PASSWORD = os.environ.get('MEROSS_PASSWORD')


if os.name == 'nt':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


class TestLimits(AioHTTPTestCase):
    test_sensors: List[ElectricityMixin]

    async def get_application(self):
        return web.Application()

    async def setUpAsync(self):
        self.meross_client = await MerossHttpClient.async_from_user_password(email=EMAIL, password=PASSWORD)

        # Look for a device to be used for this test
        manager = MerossManager(http_client=self.meross_client, max_requests_per_second=4)
        await manager.async_init()
        devices = await manager.async_device_discovery()

        self.test_sensors = manager.find_devices(device_class=ElectricityMixin)

    async def _perform_requests(self, sensor: ElectricityMixin, n_requests: int):
        tasks = []
        for i in range(n_requests):
            tasks.append(sensor.async_get_instant_metrics())
        await asyncio.gather(*tasks)

    @unittest_run_loop
    async def test_sustainable_rate(self):
        if len(self.test_sensors) < 1:
            self.skipTest("No device found for this test")

        await self._perform_requests(sensor=self.test_sensors[0], n_requests=20)

    @unittest_run_loop
    async def test_unsustainable_rate(self):
        if len(self.test_sensors) < 1:
            self.skipTest("No device found for this test")
        with self.assertRaises(RateLimitExceeded):
            await self._perform_requests(sensor=self.test_sensors[0], n_requests=200)

    async def tearDownAsync(self):
        await self.meross_client.async_logout()
