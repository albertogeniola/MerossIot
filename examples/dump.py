import asyncio
import os
import json

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

    # Issue a discovery.
    await manager.async_device_discovery()
    print_devices(manager)

    # Dump the registry.
    manager.dump_device_registry("test.dump")
    print("Registry dumped.")

    # Close the manager.
    manager.close()
    await http_api_client.async_logout()

    # Now start a new one using the dumped file, without issuing a discovery.
    http_api_client = await MerossHttpClient.async_from_user_password(email=EMAIL, password=PASSWORD)
    manager = MerossManager(http_client=http_api_client)
    await manager.async_init()
    manager.load_devices_from_dump("test.dump")
    print("Registry dump loaded.")
    print_devices(manager)

    # Close the manager.
    manager.close()
    await http_api_client.async_logout()


def print_devices(manager):
    devices = manager.find_devices()
    print(f"Discovered {len(devices)} devices:")
    for dev in devices:
        print(f". {dev.name} {dev.type} ({dev.uuid})")


if __name__ == '__main__':
    # Windows and python 3.8 requires to set up a specific event_loop_policy.
    #  On Linux and MacOSX this is not necessary.
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    loop.stop()
