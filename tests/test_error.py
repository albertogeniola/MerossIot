import os
from uuid import uuid4

from aiohttp import web
from aiohttp.test_utils import AioHTTPTestCase, unittest_run_loop

from meross_iot.controller.device import BaseDevice
from meross_iot.controller.mixins.toggle import ToggleXMixin
from meross_iot.http_api import MerossHttpClient
from meross_iot.manager import MerossManager
from meross_iot.model.enums import OnlineStatus, Namespace
from meross_iot.model.exception import CommandTimeoutError

EMAIL = os.environ.get('MEROSS_EMAIL')
PASSWORD = os.environ.get('MEROSS_PASSWORD')


class TestError(AioHTTPTestCase):
    async def get_application(self):
        return web.Application()

    async def setUpAsync(self):
        self.meross_client = await MerossHttpClient.async_from_user_password(email=EMAIL, password=PASSWORD)

        # Look for a device to be used for this test
        self.meross_manager = MerossManager(http_client=self.meross_client)
        await self.meross_manager.async_init()
        devices = await self.meross_manager.async_device_discovery()

    @unittest_run_loop
    async def test_invalid_target_device(self):
        async def send_command_to_unknown_device():
            random_uuid = uuid4()
            return await self.meross_manager.async_execute_cmd(destination_device_uuid=str(random_uuid), method='GET',
                                                               namespace=Namespace.SYSTEM_ALL, payload={})

        with self.assertRaises(CommandTimeoutError):
            await send_command_to_unknown_device()

    @unittest_run_loop
    async def test_invalid_namespace(self):
        devs = self.meross_manager.find_devices(device_class=ToggleXMixin, online_status=OnlineStatus.ONLINE)
        if len(devs) < 1:
            self.skipTest("No available/online devices found to test. Skipping...")
        dev = devs[0]

        async def send_invalid_command_to_device(dev: BaseDevice):
            res = await self.meross_manager.async_execute_cmd(destination_device_uuid=dev.uuid, method='GET',
                                                              namespace=Namespace.HUB_MTS100_MODE, payload={})
            return res

        with self.assertRaises(CommandTimeoutError):
            await send_invalid_command_to_device(dev=dev)

    @unittest_run_loop
    async def test_invalid_payload(self):
        devs = self.meross_manager.find_devices(device_class=ToggleXMixin, online_status=OnlineStatus.ONLINE)
        if len(devs) < 1:
            self.skipTest("No available/online devices found to test. Skipping...")
        dev = devs[0]

        async def send_invalid_command_to_device(dev: BaseDevice):
            return await self.meross_manager.async_execute_cmd(destination_device_uuid=dev.uuid, method='SET',
                                                               namespace=Namespace.HUB_MTS100_MODE,
                                                               payload={'temperature': 'bar'})

        with self.assertRaises(CommandTimeoutError):
            await send_invalid_command_to_device(dev=dev)

    async def tearDownAsync(self):
        await self.meross_client.async_logout()
