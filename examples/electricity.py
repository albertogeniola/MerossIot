import asyncio
import os

from meross_iot.controller.mixins.electricity import ElectricityMixin
from meross_iot.controller.mixins.garage import GarageOpenerMixin
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

    # Retrieve all the devices that implement the electricity mixin
    await manager.async_device_discovery()
    devs = manager.find_devices(device_class=ElectricityMixin)

    if len(devs) < 1:
        print("No electricity-capable device found...")
    else:
        dev = devs[0]

        # Read the electricity power/voltage/current
        instant_consumption = await dev.async_get_instant_metrics()
        print(f"Current consumption data: {instant_consumption}")

    # Close the manager and logout from http_api
    manager.close()
    await http_api_client.async_logout()

if __name__ == '__main__':
    # On Windows + Python 3.8, you should uncomment the following
    # asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    loop.close()
