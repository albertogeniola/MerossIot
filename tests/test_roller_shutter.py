import os
from typing import Union, Dict

from aiohttp import web
from aiohttp.test_utils import AioHTTPTestCase, unittest_run_loop

from meross_iot.controller.device import BaseDevice
from meross_iot.controller.mixins.roller_shutter import RollerShutterTimerMixin
from meross_iot.manager import MerossManager
from meross_iot.model.enums import OnlineStatus, Namespace, RollerShutterState
from tests import async_get_client

if os.name == 'nt':
    import asyncio
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
else:
    import asyncio


class TestRollerShutter(AioHTTPTestCase):
    test_device: Union[RollerShutterTimerMixin, BaseDevice, None]
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
        roller_devices = self.meross_manager.find_devices(device_class=RollerShutterTimerMixin, online_status=OnlineStatus.ONLINE)

        if len(roller_devices) < 1:
            self.test_device = None
        else:
            self.test_device = roller_devices[0]

    @unittest_run_loop
    async def test_open(self):
        if self.test_device is None:
            self.skipTest("No RollerShutter device has been found to run this test on.")
        print(f"Testing device {self.test_device.name}")

        # Update its status
        await self.test_device.async_update()

        state_opening = asyncio.Event()
        state_closing = asyncio.Event()
        state_idle = asyncio.Event()
        position_opened = asyncio.Event()
        position_closed = asyncio.Event()
        async def coro(namespace:Namespace, data: Dict, device_internal_id: str):
            if namespace == Namespace.ROLLER_SHUTTER_STATE:
                states = data.get('state')
                # Filter by channel
                state = next(filter(lambda s: s.get('channel')==0, states)).get('state')
                if state == RollerShutterState.OPENING.value:
                    state_opening.set()
                elif state == RollerShutterState.CLOSING.value:
                    state_closing.set()
                elif state == RollerShutterState.IDLE.value:
                    state_idle.set()
            if namespace == Namespace.ROLLER_SHUTTER_POSITION:
                positions = data.get('position')
                # Filter by channel
                position = next(filter(lambda s: s.get('channel')==0, positions)).get('position')
                if position == 100:
                    position_opened.set()
                elif position == 0:
                    position_closed.set()

        self.test_device.register_push_notification_handler_coroutine(coro)

        # Trigger the opening
        print("Sending opening command to Roller Shutter")
        await self.test_device.async_open()
        print("Waiting for state to become OPENING...")
        await asyncio.wait_for(state_opening.wait(), timeout=5.0)
        print("Waiting for state to become IDLE...")
        await asyncio.wait_for(state_idle.wait(), timeout=60.0)
        print("Waiting for position to become 100...")
        await asyncio.wait_for(position_opened.wait(), timeout=30.0)
        print("DONE!")

        self.test_device.unregister_push_notification_handler_coroutine(coro)

    @unittest_run_loop
    async def test_close(self):
        if self.test_device is None:
            self.skipTest("No RollerShutter device has been found to run this test on.")
        print(f"Testing device {self.test_device.name}")

        # Update its status
        await self.test_device.async_update()

        state_opening = asyncio.Event()
        state_closing = asyncio.Event()
        state_idle = asyncio.Event()
        position_opened = asyncio.Event()
        position_closed = asyncio.Event()
        async def coro(namespace:Namespace, data: Dict, device_internal_id: str):
            if namespace == Namespace.ROLLER_SHUTTER_STATE:
                states = data.get('state')
                # Filter by channel
                state = next(filter(lambda s: s.get('channel')==0, states)).get('state')
                if state == RollerShutterState.OPENING.value:
                    state_opening.set()
                elif state == RollerShutterState.CLOSING.value:
                    state_closing.set()
                elif state == RollerShutterState.IDLE.value:
                    state_idle.set()
            if namespace == Namespace.ROLLER_SHUTTER_POSITION:
                positions = data.get('position')
                # Filter by channel
                position = next(filter(lambda s: s.get('channel')==0, positions)).get('position')
                if position == 100:
                    position_opened.set()
                elif position == 0:
                    position_closed.set()

        self.test_device.register_push_notification_handler_coroutine(coro)

        # Trigger the closing
        print("Sending closing command to Roller Shutter")
        await self.test_device.async_close()
        print("Waiting for state to become CLOSING...")
        await asyncio.wait_for(state_closing.wait(), timeout=5.0)
        print("Waiting for state to become IDLE...")
        await asyncio.wait_for(state_idle.wait(), timeout=60.0)
        print("Waiting for position to become 0...")
        await asyncio.wait_for(position_closed.wait(), timeout=30.0)
        print("DONE!")

        self.test_device.unregister_push_notification_handler_coroutine(coro)

    async def tearDownAsync(self):
        if self.requires_logout:
            await self.meross_client.async_logout()
        self.meross_manager.close()

        # Give a change to asyncio clean everything up
        await asyncio.sleep(1)