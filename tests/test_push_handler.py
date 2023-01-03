import os
from typing import List

from aiohttp import web
from aiohttp.test_utils import AioHTTPTestCase, unittest_run_loop

from meross_iot.controller.device import BaseDevice
from meross_iot.controller.mixins.garage import GarageOpenerMixin
from meross_iot.controller.mixins.toggle import ToggleXMixin
from meross_iot.manager import MerossManager
from meross_iot.model.enums import OnlineStatus
from meross_iot.model.push.generic import GenericPushNotification
from tests import async_get_client


if os.name == 'nt':
    import asyncio
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
else:
    import asyncio


class TestPushNotificationHandler(AioHTTPTestCase):
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
        toggle_devices = self.meross_manager.find_devices(device_class=ToggleXMixin, online_status=OnlineStatus.ONLINE)
        # Exclude garage openers
        toggle_devices = list(filter(lambda x: not isinstance(x, GarageOpenerMixin), toggle_devices))
        if len(toggle_devices) < 1:
            self.test_device = None
        else:
            self.test_device = toggle_devices[0]

    @unittest_run_loop
    async def test_dev_push_notification(self):
        if self.test_device is None:
            self.skipTest("No ToggleX device has been found to run this test on.")
        print(f"Testing device {self.test_device.name}")
        # Set the toggle device to ON state
        await self.test_device.async_turn_on()

        # Create a new manager
        new_meross_client, requires_logout = await async_get_client()
        m = None
        try:
            # Retrieve the same device with another manager
            m = MerossManager(http_client=new_meross_client)
            await m.async_init()
            await m.async_device_discovery()
            devs = m.find_devices(device_uuids=(self.test_device.uuid,))
            dev = devs[0]

            mgr_e = asyncio.Event()
            dev_e = asyncio.Event()

            # Define the coroutine for handling push notification at Manager Level
            async def manager_push_handler(push: GenericPushNotification, devices: List[BaseDevice], manager: MerossManager):
                mgr_e.set()

            # Define the coroutine for handling push notification for a specific device
            async def dev_push_handler(namespace, data, device_internal_id):
                dev_e.set()

            dev.register_push_notification_handler_coroutine(dev_push_handler)
            self.meross_manager.register_push_notification_handler_coroutine(manager_push_handler)

            await self.test_device.async_turn_off()
            aws = [asyncio.create_task(mgr_e.wait()), asyncio.create_task(dev_e.wait())]
            done, pending = await asyncio.wait(aws, timeout=5.0, return_when=asyncio.ALL_COMPLETED)
            assert(len(done) == 2 and len(pending) == 0)

            # Unregister the handlers, repeat the test and make sure none of them is triggered
            dev.unregister_push_notification_handler_coroutine(dev_push_handler)
            self.meross_manager.unregister_push_notification_handler_coroutine(manager_push_handler)
            mgr_e.clear()
            dev_e.clear()

            aws = [asyncio.create_task(mgr_e.wait()), asyncio.create_task(dev_e.wait())]
            await self.test_device.async_turn_on()
            done, pending = await asyncio.wait(aws, timeout=5.0, return_when=asyncio.ALL_COMPLETED)
            assert (len(done) == 0 and len(pending) == 2)
            for task in pending:
                task.cancel()

        finally:
            if m is not None:
                m.close()
            if requires_logout:
                await new_meross_client.async_logout()

    async def tearDownAsync(self):
        if self.requires_logout:
            await self.meross_client.async_logout()
        self.meross_manager.close()

        # Give a change to asyncio clean everything up
        await asyncio.sleep(1)