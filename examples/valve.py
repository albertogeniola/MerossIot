import asyncio
import os
from random import randint

from meross_iot.http_api import MerossHttpClient
from meross_iot.manager import MerossManager

EMAIL = os.environ.get('MEROSS_EMAIL') or "YOUR_MEROSS_CLOUD_EMAIL"
PASSWORD = os.environ.get('MEROSS_PASSWORD') or "YOUR_MEROSS_CLOUD_PASSWORD"


async def main():
    # Setup the HTTP client API from user-password
    http_api_client = await MerossHttpClient.async_from_user_password(email=EMAIL, password=PASSWORD)

    # Setup and start the device manager
    manager = MerossManager(http_client=http_api_client)
    await manager.async_init()

    # Retrieve all the mts100v3 devices that are registered on this account
    await manager.async_device_discovery()
    sensors = manager.find_devices(device_type="mts100v3")

    if len(sensors) < 1:
        print("No mts100v3 plugs found...")
    else:
        dev = sensors[0]

        # Manually force and update to retrieve the latest temperature sensed from
        # the device (this ensures we get the most recent value rather than a cached one)
        await dev.async_update()

        # Access read cached data
        on_off = dev.is_on()

        # Turn on the device if it's not on
        if not on_off:
            print(f"Device {dev.name} is off, turning it on...")
            await dev.async_turn_on()

        temp = await dev.async_get_temperature()
        print(f"Current ambient temperature = {temp} °C, "
              f"Target Temperature = {dev.target_temperature}, "
              f"mode = {dev.mode},"
              f"heating = {dev.is_heating}")

        # Randomly choose a temperature between min and max
        new_temp = randint(dev.min_supported_temperature, dev.max_supported_temperature)
        print(f"Setting target temperature to {new_temp}")

    # Close the manager and logout from http_api
    manager.close()
    await http_api_client.async_logout()

if __name__ == '__main__':
    # On Windows + Python 3.8, you should uncomment the following
    # asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    loop.close()

