import asyncio
import os
from random import randint

from meross_iot.controller.subdevice_mixins.mts100_thermostat import Mts100Mixin
from meross_iot.http_api import MerossHttpClient
from meross_iot.manager import MerossManager
from meross_iot.model.enums import Namespace

EMAIL = os.environ.get('MEROSS_EMAIL') or "YOUR_MEROSS_CLOUD_EMAIL"
PASSWORD = os.environ.get('MEROSS_PASSWORD') or "YOUR_MEROSS_CLOUD_PASSWORD"


async def thermostat_event(namespace: str, data: dict, device_internal_id: str, *args, **kwargs):
    if namespace == Namespace.HUB_MTS100_MODE.value:
        print(f"Device {device_internal_id} - Thermostat MODE CHANGE -> {data}")
    elif namespace == Namespace.HUB_MTS100_ADJUST.value:
        print(f"Device {device_internal_id} - Thermostat ADJUST CHANGE -> {data}")
    elif namespace == Namespace.HUB_MTS100_TEMPERATURE.value:
        print(f"Device {device_internal_id} - Thermostat HUB_MTS100_TEMPERATURE CHANGE -> {data}")
    elif namespace == Namespace.HUB_TOGGLEX.value:
        print(f"Device {device_internal_id} - Thermostat STATE CHANGE CHANGE -> {data}")
    else:
        print("An event has occurred, but that is not a MTS100 open/close state update")


async def main():
    # Setup the HTTP client API from user-password
    http_api_client = await MerossHttpClient.async_from_user_password(email=EMAIL, password=PASSWORD, api_base_url="https://iot.meross.com")

    # Setup and start the device manager
    manager = MerossManager(http_client=http_api_client)
    await manager.async_init()

    # Retrieve all the mts100v3 devices that are registered on this account
    await manager.async_device_discovery()
    sensors = manager.find_devices(device_class=Mts100Mixin)

    if len(sensors) < 1:
        print("No mts100v3 plugs found...")
    else:
        dev: Mts100Mixin = sensors[0]

        # Register an event handler for this device
        dev.register_push_notification_handler_coroutine(thermostat_event)

        # Manually force and update to retrieve the latest temperature sensed from
        # the device (this ensures we get the most recent value rather than a cached one)
        await dev.async_update()

        for i in range(5):
            temp = await dev.async_get_temperature()
            print(f"Current ambient temperature = {temp} °C, "
                  f"Target Temperature = {dev.target_temperature}, "
                  f"mode = {dev.mode},"
                  f"heating = {dev.is_heating}")

            # Randomly choose a temperature between min and max
            new_temp = randint(int(dev.min_supported_temperature), int(dev.max_supported_temperature))
            print(f"Setting target temperature to {new_temp}")
            await dev.async_set_target_temperature(new_temp)
            print(f"Waiting 60 seconds...")
            await asyncio.sleep(60)

    # Close the manager and logout from http_api
    manager.close()
    await http_api_client.async_logout()

if __name__ == '__main__':
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    loop.stop()

