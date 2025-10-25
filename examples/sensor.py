import asyncio
import os

from meross_iot.controller.subdevice_mixins.ms100_sensor import Ms100Mixin
from meross_iot.http_api import MerossHttpClient
from meross_iot.manager import MerossManager
from meross_iot.model.enums import Namespace

EMAIL = os.environ.get('MEROSS_EMAIL') or "YOUR_MEROSS_CLOUD_EMAIL"
PASSWORD = os.environ.get('MEROSS_PASSWORD') or "YOUR_MEROSS_CLOUD_PASSWORD"


async def event_handler(namespace: Namespace, data: dict, device_internal_id: str, *args, **kwargs):
    print("An event has occurred!")


async def main():
    # Setup the HTTP client API from user-password
    http_api_client = await MerossHttpClient.async_from_user_password(email=EMAIL, password=PASSWORD, api_base_url="https://iot.meross.com")

    # Setup and start the device manager
    manager = MerossManager(http_client=http_api_client)
    await manager.async_init()

    # Retrieve all the MS100 devices that are registered on this account
    await manager.async_device_discovery()
    sensors = manager.find_devices(device_class=Ms100Mixin)

    if len(sensors) < 1:
        print("No MS100 plugs found...")
    else:
        dev = sensors[0]

        dev.register_push_notification_handler_coroutine(event_handler)

        # Manually force and update to retrieve the latest temperature sensed from
        # the device. This ensures we get the most recent data and not a cached value
        await dev.async_update()

        # Manually force and update to retrieve the latest temperature sensed from
        # the device. This ensures we get the most recent data and not a cached value
        while True:
            try:
                # In order to update the sensor's data, me must first issue an explicit UPDATE first
                await dev.async_update()
                # Access read cached data
                temp = dev.last_sampled_temperature
                humid = dev.last_sampled_humidity
                time = dev.last_sampled_time

                print(f"Current sampled data on {time.isoformat()}; Temperature={temp}°C, Humidity={humid}%. Press CTRL+C to terminate.")
                # Let's wait a bit for some events to occur
                await asyncio.sleep(10)
            except InterruptedError as e:
                print("Execution terminated by the user")

    # Close the manager and logout from http_api
    manager.close()
    await http_api_client.async_logout()

if __name__ == '__main__':
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    loop.stop()
