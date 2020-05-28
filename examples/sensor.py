import asyncio
import os

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

    # Retrieve all the MS100 devices that are registered on this account
    await manager.async_device_discovery()
    sensors = manager.find_devices(device_type="ms100")

    if len(sensors) < 1:
        print("No MS100 plugs found...")
    else:
        dev = sensors[0]

        # Manually force and update to retrieve the latest temperature sensed from
        # the device
        await dev.async_update()

        # Access read cached data
        temp = dev.last_sampled_temperature
        humid = dev.last_sampled_humidity
        time = dev.last_sampled_time

        print(f"Current sampled data on {time.isoformat()}; Temperature={temp}°C, Humidity={humid}%")
    # Close the manager and logout from http_api
    manager.close()
    await http_api_client.async_logout()

if __name__ == '__main__':
    # On Windows + Python 3.8, you should uncomment the following
    # asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    loop.close()
