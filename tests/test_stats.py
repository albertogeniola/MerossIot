import os
import time
from datetime import timedelta
from random import randint
from typing import List

from aiohttp import web
from aiohttp.test_utils import AioHTTPTestCase, unittest_run_loop

from meross_iot.controller.mixins.system import SystemAllMixin
from meross_iot.http_api import ErrorCodes
from meross_iot.manager import MerossManager
from meross_iot.model.enums import OnlineStatus
from meross_iot.utilities.limiter import RateLimitChecker
from tests import async_get_client

if os.name == 'nt':
    import asyncio
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
else:
    import asyncio


class TestStats(AioHTTPTestCase):
    async def get_application(self):
        return web.Application()

    async def setUpAsync(self):
        # Wait some time before next test-burst
        await asyncio.sleep(5)
        self.meross_client, self.requires_logout = await async_get_client()

        # Look for a device to be used for this test
        self.meross_manager = MerossManager(http_client=self.meross_client)
        await self.meross_manager.async_init()
        devices = await self.meross_manager.async_device_discovery()
        self.devices: List[SystemAllMixin] = self.meross_manager.find_devices(device_class=SystemAllMixin, online_status=OnlineStatus.ONLINE)

    async def _run_test(self, n_devices: int, n_commands: int) -> None:
        if len(self.devices) < n_devices:
            self.skipTest("Not enough devices found to test .")

        devices = self.devices[:n_devices]
        print("Testing with following devices:")
        for d in devices:
            print(f". {d.name} - {d.type} [{d.uuid}]")

        # Let's issue n_commands (one every second) per each device in parallel.
        # We expect to get n_commands*n_devices issued totally, n_commands per each device within the last 10 seconds
        async def coro_task(d: SystemAllMixin):
            for i in range(0, n_commands):
                r = await d.async_update()
                await asyncio.sleep(1)

        tasks = []
        for d in devices:
            tasks.append(asyncio.create_task(coro_task(d)))

        await asyncio.gather(*tasks)

    @unittest_run_loop
    async def test_mqtt_call_stats(self):
        n_devices = 2
        n_commands = 3
        timewindow_seconds = 10

        # Wait 10 seconds to reset stats
        print(f"Waiting {timewindow_seconds} seconds before starting the test.")
        await asyncio.sleep(timewindow_seconds)

        await self._run_test(n_devices=n_devices, n_commands=n_commands)
        stats = self.meross_manager.mqtt_call_stats.get_api_stats(time_window=timedelta(seconds=timewindow_seconds + 0.5))

        # Make sure the total number of issued commands is OK
        self.assertEqual(stats.global_stats.total_calls, n_devices * n_commands)

        # Make sure each device has recorder n_commands
        for uuid, stats in stats.device_stats():
            self.assertEqual(stats.total_calls, n_commands)

    @unittest_run_loop
    async def test_mqtt_delay(self):
        n_devices = 2
        n_commands = 10
        timewindow_seconds = 30

        # Wait to reset stats
        print(f"Waiting {timewindow_seconds} seconds before starting the test, so we reset the stats")
        await asyncio.sleep(timewindow_seconds)

        start = time.time()

        # Setup the manager limiter
        # perform at most 1 global calls in a burst rate, filled 1 call/sec
        # Allow at most 1 call/second per each device, with a burst rate of 1 call.
        self.meross_manager.limiter = RateLimitChecker(global_burst_rate=1,
                                                       global_time_window=timedelta(seconds=1),
                                                       global_tokens_per_interval=1,
                                                       device_burst_rate=1,
                                                       device_time_window=timedelta(seconds=1),
                                                       device_tokens_per_interval=1,
                                                       device_max_command_queue=40
                                                       )
        # This will issue 20 commands, 2 commands at a second (in parallel).
        # Since the global burst rate is limited to 1 command and it grows as 1 command/second,
        # we expect 10 over 20 commands to be delayed.
        await self._run_test(n_devices=n_devices, n_commands=n_commands)

        # Wait for the window to complete
        now = time.time()
        elapsed = now-start
        remaining = timewindow_seconds - elapsed
        if remaining > 0:
            print(f"Waiting {remaining} seconds before calculating the stats")
            await asyncio.sleep(remaining)

        call_stats = self.meross_manager.mqtt_call_stats.get_api_stats(time_window=timedelta(seconds=timewindow_seconds + 0.5))
        delay_stats = self.meross_manager.mqtt_call_stats.get_delayed_api_stats(
            time_window=timedelta(seconds=timewindow_seconds + 0.5))
        drop_stats = self.meross_manager.mqtt_call_stats.get_dropped_api_stats(
            time_window=timedelta(seconds=timewindow_seconds + 0.5))

        # Make sure at least 10 commands have been delayed
        self.assertGreater(delay_stats.global_stats.total_calls, 10)

        # Make sure all commands have been executed
        self.assertEqual(call_stats.global_stats.total_calls, 20)

        # Make sure no command has been dropped
        self.assertEqual(drop_stats.global_stats.total_calls, 0)

    @unittest_run_loop
    async def test_http_call_stats(self):
        timewindow_seconds = 10

        # Wait 10 seconds to reset stats
        print(f"Waiting {timewindow_seconds} seconds before starting the test.")
        await asyncio.sleep(timewindow_seconds)

        # Get http client
        client = self.meross_client

        # Call discovery api for n times
        ok_calls = randint(3, 6)
        for i in range(ok_calls):
            await client.async_list_devices()
            await asyncio.sleep(.2)

        # Call a bad api for m times
        ko_calls = randint(2, 5)
        for i in range(ko_calls):
            try:
                await client.async_login(email="notexisting", password="invalid", stats_counter=client.stats)
            except Exception as e:
                print(e)
                pass
            await asyncio.sleep(.2)

        # Check stats
        stats = client.stats.get_stats(time_window=timedelta(seconds=timewindow_seconds + 0.5))

        # Make sure the total number of issued commands is OK
        print(f"ok_calls: {ok_calls}, ko_calls: {ko_calls}, all: {ok_calls+ko_calls}")
        self.assertEqual(stats.global_stats.total_calls, ok_calls+ko_calls)

        failures = 0
        for code, count in stats.global_stats.by_api_status_code():
            if code == ErrorCodes.CODE_NO_ERROR:
                # Make sure we count n OK calls
                self.assertEqual(count, ok_calls)
            else:
                failures += count

        # Make sure we count m Failed calls
        self.assertEqual(failures, ko_calls)

    async def tearDownAsync(self):
        if self.requires_logout:
            await self.meross_client.async_logout()
        self.meross_manager.close()

        # Give a change to asyncio clean everything up
        await asyncio.sleep(1, loop=self.meross_manager._loop)