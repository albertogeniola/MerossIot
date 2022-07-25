import os
import random
from random import randint
from typing import List, TypeVar

from aiohttp import web
from aiohttp.test_utils import AioHTTPTestCase, unittest_run_loop

from meross_iot.controller.device import BaseDevice
from meross_iot.controller.mixins.thermostat import ThermostatModeMixin
from meross_iot.manager import MerossManager
from meross_iot.model.enums import OnlineStatus, ThermostatMode
from tests import async_get_client

if os.name == 'nt':
    import asyncio

    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
else:
    import asyncio

Mts200Type = TypeVar('Mts200Type', BaseDevice, ThermostatModeMixin)


class TestThermostat(AioHTTPTestCase):
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
        self.test_devices: List[Mts200Type] = self.meross_manager.find_devices(device_class=ThermostatModeMixin, online_status=OnlineStatus.ONLINE)

    @unittest_run_loop
    async def test_on_off(self):
        if len(self.test_devices) < 1:
            self.skipTest("No valve device has been found to run this test.")

        dev = self.test_devices[0]
        print(f"Testing device {dev.name}")
        await dev.async_update()
        state = dev.get_thermostat_state()
        toggled_state = not state.is_on
        await dev.async_set_thermostat_config(on_not_off=toggled_state)
        self.assertEqual(dev.get_thermostat_state().is_on, toggled_state)

    @unittest_run_loop
    async def test_ambient_temperature(self):
        if len(self.test_devices) < 1:
            self.skipTest("No valve device has been found to run this test.")

        for dev in self.test_devices:
            print(f"Testing device {dev.name}")
            res = await dev.async_update()
            temperature = dev.get_thermostat_state().current_temperature_celsius
            print(f"Thermostat {dev.name} reports ambiente temperature of {temperature} °C")
            self.assertIsInstance(temperature, float)

    @unittest_run_loop
    async def test_mode(self):
        if len(self.test_devices) < 1:
            self.skipTest("No valve device has been found to run this test.")

        dev = self.test_devices[0]
        print(f"Testing device {dev.name}")
        await dev.async_update()
        state = dev.get_thermostat_state()
        self.assertIsNotNone(state.mode)
        modes = set(ThermostatMode)
        modes.remove(state.mode)
        modes = list(modes)
        index = randint(0, len(modes)-1)
        target_mode = modes[index]

        await dev.async_set_thermostat_config(mode=target_mode)
        self.assertEqual(target_mode, dev.get_thermostat_state().mode)

    def _align_temp(self, temperature:float) -> float:
        # Round temp value to 0.5
        quotient = temperature/0.5
        quotient = round(quotient)
        final_temp = quotient*0.5
        return final_temp

    @unittest_run_loop
    async def test_eco_temp(self):
        if len(self.test_devices) < 1:
            self.skipTest("No valve device has been found to run this test.")

        dev = self.test_devices[0]
        print(f"Testing device {dev.name}")
        await dev.async_update()
        state = dev.get_thermostat_state()
        min_temp = state.min_temperature_celsius
        max_temp = state.max_temperature_celsius
        target_temp = min_temp + random.random()* (max_temp-min_temp)
        target_temp = self._align_temp(target_temp)
        # Set eco temp mode
        await dev.async_set_thermostat_config(eco_temperature_celsius=target_temp)
        # Ensure eco temp mode has been updated
        self.assertEqual(dev.get_thermostat_state().eco_temperature_celsius, target_temp)
        # Set eco mode
        await dev.async_set_thermostat_config(mode=ThermostatMode.ECONOMY)
        self.assertEqual(dev.get_thermostat_state().mode, ThermostatMode.ECONOMY)

    @unittest_run_loop
    async def test_cool_temp(self):
        if len(self.test_devices) < 1:
            self.skipTest("No valve device has been found to run this test.")

        dev = self.test_devices[0]
        print(f"Testing device {dev.name}")
        await dev.async_update()
        state = dev.get_thermostat_state()
        min_temp = state.min_temperature_celsius
        max_temp = state.max_temperature_celsius
        target_temp = min_temp + random.random() * (max_temp - min_temp)
        target_temp = self._align_temp(target_temp)
        # Set eco temp mode
        await dev.async_set_thermostat_config(cool_temperature_celsius=target_temp)
        # Ensure eco temp mode has been updated
        self.assertEqual(dev.get_thermostat_state().cool_temperature_celsius, target_temp)
        # Set eco mode
        await dev.async_set_thermostat_config(mode=ThermostatMode.COOL)
        self.assertEqual(dev.get_thermostat_state().mode, ThermostatMode.COOL)

    @unittest_run_loop
    async def test_heat_temp(self):
        if len(self.test_devices) < 1:
            self.skipTest("No valve device has been found to run this test.")

        dev = self.test_devices[0]
        print(f"Testing device {dev.name}")
        await dev.async_update()
        state = dev.get_thermostat_state()
        min_temp = state.min_temperature_celsius
        max_temp = state.max_temperature_celsius
        target_temp = min_temp + random.random() * (max_temp - min_temp)
        target_temp = self._align_temp(target_temp)
        # Set eco temp mode
        await dev.async_set_thermostat_config(heat_temperature_celsius=target_temp)
        # Ensure eco temp mode has been updated
        self.assertEqual(dev.get_thermostat_state().heat_temperature_celsius, target_temp)
        # Set eco mode
        await dev.async_set_thermostat_config(mode=ThermostatMode.HEAT)
        self.assertEqual(dev.get_thermostat_state().mode, ThermostatMode.HEAT)

    @unittest_run_loop
    async def test_manual_temp(self):
        if len(self.test_devices) < 1:
            self.skipTest("No valve device has been found to run this test.")

        dev = self.test_devices[0]
        print(f"Testing device {dev.name}")
        await dev.async_update()
        state = dev.get_thermostat_state()
        min_temp = state.min_temperature_celsius
        max_temp = state.max_temperature_celsius
        target_temp = min_temp + random.random() * (max_temp - min_temp)
        target_temp = self._align_temp(target_temp)
        # Set eco temp mode
        await dev.async_set_thermostat_config(manual_temperature_celsius=target_temp)
        # Ensure eco temp mode has been updated
        self.assertEqual(dev.get_thermostat_state().manual_temperature_celsius, target_temp)
        # Set eco mode
        await dev.async_set_thermostat_config(mode=ThermostatMode.MANUAL)
        self.assertEqual(dev.get_thermostat_state().mode, ThermostatMode.MANUAL)

    @unittest_run_loop
    async def test_onoff(self):
        if len(self.test_devices) < 1:
            self.skipTest("No valve device has been found to run this test.")

        for dev in self.test_devices:
            print(f"Testing device {dev.name}")
            res = await dev.async_update()

            # Turn off
            await dev.async_set_thermostat_config(on_not_off=False)
            self.assertFalse(dev.get_thermostat_state().is_on)
            await asyncio.sleep(1)
            # Turn on
            await dev.async_set_thermostat_config(on_not_off=True)
            self.assertTrue(dev.get_thermostat_state().is_on)
            await asyncio.sleep(1)
            # Turn off
            await dev.async_set_thermostat_config(on_not_off=False)
            self.assertFalse(dev.get_thermostat_state().is_on)
            await asyncio.sleep(1)

    #
    # @unittest_run_loop
    # async def test_push_notification(self):
    #     if len(self.test_devices) < 1:
    #         self.skipTest("No valve device has been found to run this test.")
    #
    #     dev1 = self.test_devices[0]
    #     print(f"Testing device {dev1.name}")
    #     # Turn it on
    #     await dev1.async_turn_on()
    #
    #     # Create a new manager
    #     new_meross_client, requires_logout = await async_get_client()
    #     m = None
    #     try:
    #         # Retrieve the same device with another manager
    #         m = MerossManager(http_client=new_meross_client)
    #         await m.async_init()
    #         await m.async_device_discovery()
    #         devs = m.find_devices(internal_ids=(dev1.internal_id,))
    #         dev = devs[0]
    #
    #         await dev.async_update()
    #         await dev1.async_update()
    #
    #         # Set target temperature to a random state
    #         target = randint(dev.min_supported_temperature, dev.max_supported_temperature)
    #         print(f"TARGET = {target}...")
    #         await dev1.async_set_target_temperature(temperature=target)
    #
    #         # The manager that issues the command would immediately update the local state, so we can check
    #         # its update as soon as the command is issued.
    #         dev1_target_temp = dev1.target_temperature
    #         print(f"DEV1 = {dev1_target_temp}...")
    #         self.assertEqual(dev1_target_temp, target)
    #
    #         # Wait a bit: give time for the push notification to get received on the other manager...
    #         await asyncio.sleep(5)
    #         # Make sure the other manager has received the push notification event
    #         dev_target_temp = dev.target_temperature
    #         print(f"DEV = {dev_target_temp}...")
    #         self.assertEqual(dev_target_temp, target)
    #
    #     finally:
    #         if m is not None:
    #             m.close()
    #         if requires_logout:
    #             await new_meross_client.async_logout()

    async def tearDownAsync(self):
        if self.requires_logout:
            await self.meross_client.async_logout()
        self.meross_manager.close()

        # Give a change to asyncio clean everything up
        await asyncio.sleep(1)
