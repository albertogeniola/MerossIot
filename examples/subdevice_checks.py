import asyncio
import os
from typing import List

from meross_iot.controller.device import GenericSubDevice
from meross_iot.controller.mixins.hub import HubMixin
from meross_iot.controller.subdevice_mixins.leakage_sensor import LeakageSensorMixin
from meross_iot.http_api import MerossHttpClient
from meross_iot.manager import MerossManager
from meross_iot.model.enums import Namespace, OnlineStatus

EMAIL = os.environ.get('MEROSS_EMAIL') or "YOUR_MEROSS_CLOUD_EMAIL"
PASSWORD = os.environ.get('MEROSS_PASSWORD') or "YOUR_MEROSS_CLOUD_PASSWORD"


async def event_handler(namespace: Namespace, data: dict, device_internal_id: str, *args, **kwargs):
    print(f"An event occurred: {namespace}, Event data: {data}")


async def main():
    # Set up the HTTP client API from user-password
    http_api_client = await MerossHttpClient.async_from_user_password(email=EMAIL, password=PASSWORD, api_base_url="https://iot.meross.com")

    # Setup and start the device manager
    manager = MerossManager(http_client=http_api_client)

    # Discover devices and subdevices
    await manager.async_device_discovery()

    # Filter all hubs and issue a full update on them.
    # This will trigger the SYSTEM_ALL MixIn
    hubs: List[HubMixin] = manager.find_devices(device_class=HubMixin, online_status=OnlineStatus.ONLINE)

    if len(hubs) < 1:
        print("No online hubs sensors found!")
    else:
        # Let's register an event handle to quickly react in case of water leaks
        for hub in hubs:
            hub.register_push_notification_handler_coroutine(event_handler)

        # Manually force and update to retrieve the latest temperature sensed from
        # the device. This ensures we get the most recent data and not a cached value
        while True:
            try:
                for hub in hubs:
                    print("Updating data for hub.")
                    await hub.async_update()
                await asyncio.sleep(60)
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
