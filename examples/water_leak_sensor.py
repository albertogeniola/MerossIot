import asyncio
import os

from meross_iot.http_api import MerossHttpClient
from meross_iot.manager import MerossManager

EMAIL = os.environ.get('MEROSS_EMAIL') or "YOUR_MEROSS_CLOUD_EMAIL"
PASSWORD = os.environ.get('MEROSS_PASSWORD') or "YOUR_MEROSS_CLOUD_PASSWORD"


async def main():
    # Setup the HTTP client API from user-password
    http_api_client = await MerossHttpClient.async_from_user_password(email=EMAIL, password=PASSWORD, api_base_url="https://iot.meross.com")

    # Setup and start the device manager
    manager = MerossManager(http_client=http_api_client)
    await manager.async_init()

    # Retrieve all the MS100 devices that are registered on this account
    await manager.async_device_discovery()

    msh400 = manager.find_devices(device_type="msh400")
    hub = msh400[0]


    water_leak_sensors = manager.find_devices(device_type="ms405")

    if len(water_leak_sensors) < 1:
        print("No MSH405 sensor found...")
    else:
        dev = water_leak_sensors[0]

        # Manually force and update to retrieve the latest temperature sensed from
        # the device. This ensures we get the most recent data and not a cached value
        await dev.async_update()

        # Access read cached data
        print(f"IS_LEAKING={dev.is_leaking}")

        # Let's wait a bit for some events to occur
        await asyncio.sleep(3600)

    # Close the manager and logout from http_api
    manager.close()
    await http_api_client.async_logout()

if __name__ == '__main__':
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    loop.stop()
