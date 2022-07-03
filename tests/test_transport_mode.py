import logging
import os

from aiohttp import web
from aiohttp.test_utils import AioHTTPTestCase, unittest_run_loop

from meross_iot.controller.mixins.toggle import ToggleXMixin
from meross_iot.manager import MerossManager, TransportMode
from meross_iot.model.enums import OnlineStatus
from tests import async_get_client

if os.name == 'nt':
    import asyncio
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
else:
    import asyncio


_LOGGER = logging.getLogger()
_LOGGER.setLevel(logging.DEBUG)


class TestTransportMode(AioHTTPTestCase):
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
        toggle_devices = self.meross_manager.find_devices(online_status=OnlineStatus.ONLINE, device_class=ToggleXMixin)

        if len(toggle_devices) < 1:
            self.test_device = None
        else:
            self.test_device = toggle_devices[0]

    @unittest_run_loop
    async def test_update_default_transport_http_first(self):
        if self.test_device is None:
            self.skipTest("No device has been found to run this test on.")
        print(f"Testing device {self.test_device.name}")

        self.meross_manager.default_transport_mode = TransportMode.LAN_HTTP_FIRST

        for i in range(10):
            await self.test_device.async_update()
            await asyncio.sleep(1.0)

        self.meross_manager.default_transport_mode = TransportMode.MQTT_ONLY

    @unittest_run_loop
    async def test_update_default_transport_http_first_only_get(self):
        # Executes high rate updates via MQTT, and will probably fail
        if self.test_device is None:
            self.skipTest("No device has been found to run this test on.")
        print(f"Testing device {self.test_device.name}")

        self.meross_manager.default_transport_mode = TransportMode.LAN_HTTP_FIRST_ONLY_GET

        for i in range(10):
            await self.test_device.async_update()
            await asyncio.sleep(1.0)
            await self.test_device.async_toggle()

    @unittest_run_loop
    async def test_update_default_transport_http_first_with_errors(self):
        if self.test_device is None:
            self.skipTest("No device has been found to run this test on.")
        print(f"Testing device {self.test_device.name}")
        prev_lan_ip = self.test_device._inner_ip
        try:
            self.meross_manager.default_transport_mode = TransportMode.LAN_HTTP_FIRST

            # Set an invalid IP, this will make all HTTP request fail and be retried via MQTT
            self.test_device._inner_ip = "2.2.2.2"
            for i in range(10):
                await self.test_device.async_update()
                await asyncio.sleep(1.0)
                await self.test_device.async_toggle()
        except:
            self.test_device._inner_ip = prev_lan_ip
            raise

    async def tearDownAsync(self):
        if self.requires_logout:
            await self.meross_client.async_logout()
        self.meross_manager.close()

        # Give a change to asyncio clean everything up
        await asyncio.sleep(1)