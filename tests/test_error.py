import os
from uuid import uuid4
from aiohttp import web
from aiohttp.test_utils import AioHTTPTestCase, unittest_run_loop

from meross_iot.controller.device import BaseDevice
from meross_iot.controller.mixins.toggle import ToggleXMixin
from meross_iot.manager import MerossManager
from meross_iot.model.constants import DEFAULT_MQTT_HOST, DEFAULT_MQTT_PORT
from meross_iot.model.enums import OnlineStatus, Namespace
from meross_iot.model.exception import CommandTimeoutError
from tests import async_get_client


if os.name == 'nt':
    import asyncio

    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
else:
    import asyncio


class TestError(AioHTTPTestCase):
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

    @unittest_run_loop
    async def test_invalid_target_device(self):
        async def send_command_to_unknown_device():
            random_uuid = uuid4()
            return await self.meross_manager.async_execute_cmd(destination_device_uuid=str(random_uuid),
                                                               method='GET',
                                                               namespace=Namespace.SYSTEM_ALL,
                                                               payload={},
                                                               mqtt_hostname=DEFAULT_MQTT_HOST,
                                                               mqtt_port=DEFAULT_MQTT_PORT)

        with self.assertRaises(CommandTimeoutError):
            await send_command_to_unknown_device()

    @unittest_run_loop
    async def test_invalid_namespace(self):
        devs = self.meross_manager.find_devices(device_class=ToggleXMixin, online_status=OnlineStatus.ONLINE)
        if len(devs) < 1:
            self.skipTest("No available/online devices found to test. Skipping...")
        dev = devs[0]
        print(f"Testing device {dev.name}")
        async def send_invalid_command_to_device(dev: BaseDevice):
            res = await self.meross_manager.async_execute_cmd(destination_device_uuid=dev.uuid,
                                                              method='GET',
                                                              namespace=Namespace.HUB_MTS100_MODE,
                                                              payload={},
                                                              mqtt_hostname=dev.mqtt_host,
                                                              mqtt_port=dev.mqtt_port)
            return res

        with self.assertRaises(CommandTimeoutError):
            await send_invalid_command_to_device(dev=dev)

    @unittest_run_loop
    async def test_invalid_payload(self):
        devs = self.meross_manager.find_devices(device_class=ToggleXMixin, online_status=OnlineStatus.ONLINE)
        if len(devs) < 1:
            self.skipTest("No available/online devices found to test. Skipping...")
        dev = devs[0]
        print(f"Testing device {dev.name}")
        async def send_invalid_command_to_device(dev: BaseDevice):
            return await self.meross_manager.async_execute_cmd(destination_device_uuid=dev.uuid,
                                                               method='SET',
                                                               namespace=Namespace.HUB_MTS100_MODE,
                                                               payload={'temperature': 'bar'},
                                                               mqtt_hostname=dev.mqtt_host,
                                                               mqtt_port=dev.mqtt_port)

        with self.assertRaises(CommandTimeoutError):
            await send_invalid_command_to_device(dev=dev)

    async def tearDownAsync(self):
        if self.requires_logout:
            await self.meross_client.async_logout()
        self.meross_manager.close()

        # Give a change to asyncio clean everything up
        await asyncio.sleep(1)
