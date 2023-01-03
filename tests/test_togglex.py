import os

from aiohttp import web
from aiohttp.test_utils import AioHTTPTestCase, unittest_run_loop

from meross_iot.controller.mixins.garage import GarageOpenerMixin
from meross_iot.controller.mixins.toggle import ToggleXMixin
from meross_iot.http_api import MerossHttpClient
from meross_iot.manager import MerossManager
from meross_iot.model.enums import OnlineStatus
from tests import async_get_client

if os.name == 'nt':
    import asyncio
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
else:
    import asyncio


class TestToggleX(AioHTTPTestCase):
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
        self.toggle_devices = self.meross_manager.find_devices(device_class=ToggleXMixin, online_status=OnlineStatus.ONLINE)
        # Filter away garage openers: they are tested independently.
        self.toggle_devices = list(filter(lambda x: not isinstance(x, GarageOpenerMixin), self.toggle_devices))

        if len(self.toggle_devices) < 1:
            self.test_device = None
        else:
            self.test_device = self.toggle_devices[0]

    @unittest_run_loop
    async def test_toggle_local_state(self):
        if self.test_device is None:
            self.skipTest("No ToggleX device has been found to run this test on.")
        print(f"Testing device {self.test_device.name}")
        # Turn off device to start from a clean state
        r = await self.test_device.async_turn_off()

        # Turn on the device
        r = await self.test_device.async_turn_on()
        self.assertTrue(self.test_device.is_on())

        # Turn off the device
        await asyncio.sleep(1)
        r = await self.test_device.async_turn_off()
        self.assertFalse(self.test_device.is_on())

    @unittest_run_loop
    async def test_toggle_multi_channel(self):
        # Search for a device with multiple channels
        multi_channel_devices = list(filter(lambda d: len(d.channels) > 1, self.toggle_devices))
        if len(multi_channel_devices) < 1:
            self.skipTest("Could not find any online device supporting more than 1 channel")

        # Toggle non master switches
        d = multi_channel_devices[0]
        print(f"Testing device {d.name}")
        for c in d.channels:
            if c.is_master_channel:
                continue
            await d.async_turn_on(channel=c.index)
            self.assertEqual(d.is_on(channel=c.index), True)
            await asyncio.sleep(1)
            await d.async_turn_off(channel=c.index)
            self.assertEqual(d.is_on(channel=c.index), False)

    @unittest_run_loop
    async def test_toggle_master_switch(self):
        # Search for a device with multiple channels
        multi_channel_devices = list(filter(lambda d: len(d.channels) > 1, self.toggle_devices))
        if len(multi_channel_devices) < 1:
            self.skipTest("Could not find any online device supporting more than 1 channel")

        # Turn on non-master switches
        d = multi_channel_devices[0]
        print(f"Testing device {d.name}")
        master = None
        for c in d.channels:
            if c.is_master_channel:
                master = c
                continue
            await d.async_turn_on(channel=c.index)
            self.assertEqual(d.is_on(channel=c.index), True)

        await asyncio.sleep(1)

        # Turn-off master switch
        self.assertIsNotNone(master)
        await d.async_turn_off(channel=master.index)

        # Give some time to the library to get the PUSH notification
        # Then make sure that the master switch has turned off all the available switches.
        await asyncio.sleep(2)
        for c in d.channels:
            self.assertEqual(d.is_on(channel=c.index), False)

    @unittest_run_loop
    async def test_usb_switches(self):
        # Search for a device with usb channel
        usb_dev = None
        usb_channel = None
        for d in self.toggle_devices:
            for c in d.channels:
                if c.is_usb:
                    usb_dev = d
                    usb_channel = c
                    break
            if usb_dev is not None:
                break

        if usb_dev is None:
            self.skipTest("Could not find any device with an usb channel")
        print(f"Testing device {usb_dev.name}")
        # Turn the channel off
        await usb_dev.async_turn_off(channel=usb_channel.index)
        self.assertFalse(usb_dev.is_on(channel=usb_channel.index))
        await asyncio.sleep(1)
        await usb_dev.async_turn_on(channel=usb_channel.index)
        self.assertTrue(usb_dev.is_on(channel=usb_channel.index))

    @unittest_run_loop
    async def test_toggle_push_notification(self):
        if self.test_device is None:
            self.skipTest("No ToggleX device has been found to run this test on.")
        print(f"Testing device {self.test_device.name}")
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

            # Turn off device to start from a clean state
            r = await self.test_device.async_turn_off()
            await asyncio.sleep(2)

            # Turn on the device
            r = await self.test_device.async_turn_on()
            # Wait a bit and make sure the other manager received the push notification
            await asyncio.sleep(2)
            self.assertTrue(self.test_device.is_on())
            self.assertTrue(dev.is_on())

            # Turn off the device
            await asyncio.sleep(1)
            r = await self.test_device.async_turn_off()
            # Wait a bit and make sure the other manager received the push notification
            await asyncio.sleep(2)
            self.assertFalse(self.test_device.is_on())
            self.assertFalse(dev.is_on())

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