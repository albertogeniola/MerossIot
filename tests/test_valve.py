from random import randint

from aiohttp import web
from aiohttp.test_utils import AioHTTPTestCase, unittest_run_loop
from meross_iot.controller.subdevice import Mts100v3Valve
from meross_iot.manager import MerossManager
from meross_iot.model.enums import ThermostatV3Mode, OnlineStatus
from meross_iot.model.plugin.hub import BatteryInfo
from tests import async_get_client
import os


if os.name == 'nt':
    import asyncio

    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
else:
    import asyncio


class TestValve(AioHTTPTestCase):
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
        self.test_devices = self.meross_manager.find_devices(device_class=Mts100v3Valve, online_status=OnlineStatus.ONLINE)

    @unittest_run_loop
    async def test_ambient_temperature(self):
        if len(self.test_devices) < 1:
            self.skipTest("No valve device has been found to run this test.")

        for dev in self.test_devices:
            print(f"Testing device {dev.name}")
            res = await dev.async_update()
            temperature = await dev.async_get_temperature()
            self.assertIsInstance(temperature, float)

    @unittest_run_loop
    async def test_presets(self):
        if len(self.test_devices) < 1:
            self.skipTest("No valve device has been found to run this test.")

        for dev in self.test_devices:
            print(f"Testing device {dev.name}")
            res = await dev.async_update()

            max_supported_temp = dev.max_supported_temperature
            min_supported_temp = dev.min_supported_temperature

            self.assertGreater(len(dev.get_supported_presets()), 0)
            for preset in dev.get_supported_presets():
                old_preset_temp = dev.get_preset_temperature(preset)
                self.assertIsNotNone(old_preset_temp)
                new_preset = randint(min_supported_temp, max_supported_temp)
                await dev.async_set_preset_temperature(preset=preset, temperature=new_preset)
                new_current_preset = dev.get_preset_temperature(preset)
                self.assertEqual(new_current_preset, new_preset)

    @unittest_run_loop
    async def test_mode(self):
        if len(self.test_devices) < 1:
            self.skipTest("No valve device has been found to run this test.")

        dev = self.test_devices[0]
        print(f"Testing device {dev.name}")
        await dev.async_update()
        self.assertIsNotNone(dev.mode)
        modes = set(ThermostatV3Mode)
        modes.remove(dev.mode)
        modes = list(modes)
        index = randint(0, len(modes)-1)
        target_mode = modes[index]

        await dev.async_set_mode(mode=target_mode)
        self.assertEqual(target_mode, dev.mode)

    @unittest_run_loop
    async def test_onoff(self):
        if len(self.test_devices) < 1:
            self.skipTest("No valve device has been found to run this test.")

        for dev in self.test_devices:
            print(f"Testing device {dev.name}")
            res = await dev.async_update()

            if dev.is_on():
                await dev.async_turn_off()
                self.assertFalse(dev.is_on())
                await asyncio.sleep(1)
                await dev.async_turn_on()
                self.assertTrue(dev.is_on())

    @unittest_run_loop
    async def test_battery(self):
        if len(self.test_devices) < 1:
            self.skipTest("No valve device has been found to run this test.")

        dev = self.test_devices[0]
        print(f"Testing device {dev.name}")
        await dev.async_update()
        res = await dev.async_get_battery_life()

        self.assertIsInstance(res, BatteryInfo)
        self.assertGreater(res.remaining_charge, -1)

    @unittest_run_loop
    async def test_push_notification(self):
        if len(self.test_devices) < 1:
            self.skipTest("No valve device has been found to run this test.")

        dev1 = self.test_devices[0]
        print(f"Testing device {dev1.name}")
        # Turn it on
        await dev1.async_turn_on()

        # Create a new manager
        new_meross_client, requires_logout = await async_get_client()
        m = None
        try:
            # Retrieve the same device with another manager
            m = MerossManager(http_client=new_meross_client)
            await m.async_init()
            await m.async_device_discovery()
            devs = m.find_devices(internal_ids=(dev1.internal_id,))
            dev = devs[0]

            await dev.async_update()
            await dev1.async_update()

            # Set target temperature to a random state
            target = randint(dev.min_supported_temperature, dev.max_supported_temperature)
            print(f"TARGET = {target}...")
            await dev1.async_set_target_temperature(temperature=target)

            # The manager that issues the command would immediately update the local state, so we can check
            # its update as soon as the command is issued.
            dev1_target_temp = dev1.target_temperature
            print(f"DEV1 = {dev1_target_temp}...")
            self.assertEqual(dev1_target_temp, target)

            # Wait a bit: give time for the push notification to get received on the other manager...
            await asyncio.sleep(5)
            # Make sure the other manager has received the push notification event
            dev_target_temp = dev.target_temperature
            print(f"DEV = {dev_target_temp}...")
            self.assertEqual(dev_target_temp, target)

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
