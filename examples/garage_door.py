import asyncio
import os
from typing import List

from meross_iot.controller.mixins.garage import GarageOpenerMixin
from meross_iot.http_api import MerossHttpClient
from meross_iot.manager import MerossManager

EMAIL = os.environ.get('MEROSS_EMAIL') or "YOUR_MEROSS_CLOUD_EMAIL"
PASSWORD = os.environ.get('MEROSS_PASSWORD') or "YOUR_MEROSS_CLOUD_PASSWORD"


async def main():
    # Setup the HTTP client API from user-password
    http_api_client = await MerossHttpClient.async_from_user_password(email=EMAIL, password=PASSWORD, api_base_url="https://iot.meross.com")

    # Setup and start the device manager
    manager = MerossManager(http_client=http_api_client)

    # Retrieve all the devices that implement the garage-door opening mixin
    await manager.async_device_discovery()
    openers: List[GarageOpenerMixin] = manager.find_devices(device_class=GarageOpenerMixin, device_type="msg200")

    if len(openers) < 1:
        print("No garage opener found...")
    else:
        dev = openers[0]

        # Update device status: this is needed only the very first time we play with this device (or if the
        #  connection goes down)
        await dev.async_update()

        # Check current door status.
        open_status = dev.garage_opener_is_open()
        if open_status:
            print(f"Door {dev.name} is open")
        else:
            print(f"Door {dev.name} is closed")

        # Let's disable the buzzer for all channels
        await dev.async_garage_opener_set_config(1, buzzer_enable=False)
        await dev.async_garage_opener_set_config(2, buzzer_enable=False)
        await dev.async_garage_opener_set_config(3, buzzer_enable=False)

        # To open the door, uncomment the following:
        print(f"Opening door {dev.name}...")
        await dev.async_garage_opener_open(2)
        print("Door opened!")

        # Wait a bit before closing it again
        await asyncio.sleep(5)
        print(f"Closing door {dev.name}...")
        await dev.async_garage_opener_close(2)
        print(f"Door closed!")

        # We can also disable the door
        print(f"Disabling door 1 for {dev.name}...")
        await dev.async_garage_opener_set_config(1, door_enable=False)
        # If you now look at the app, the door1 will disappear!
        await asyncio.sleep(5)
        # Let re-enable it.
        await dev.async_garage_opener_set_config(1, door_enable=True)
        await asyncio.sleep(5)

    # Close the manager and logout from http_api
    manager.close()
    await http_api_client.async_logout()

if __name__ == '__main__':
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    loop.stop()
