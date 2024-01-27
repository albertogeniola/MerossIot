import asyncio
import os

from meross_iot.controller.mixins.roller_shutter import RollerShutterTimerMixin
from meross_iot.http_api import MerossHttpClient
from meross_iot.manager import MerossManager
from meross_iot.model.enums import OnlineStatus

EMAIL = os.environ.get('MEROSS_EMAIL') or "YOUR_MEROSS_CLOUD_EMAIL"
PASSWORD = os.environ.get('MEROSS_PASSWORD') or "YOUR_MEROSS_CLOUD_PASSWORD"


async def main():
    # Setup the HTTP client API from user-password
    http_api_client = await MerossHttpClient.async_from_user_password(email=EMAIL, password=PASSWORD, api_base_url="https://iot.meross.com")

    # Setup and start the device manager
    manager = MerossManager(http_client=http_api_client)
    await manager.async_init()

    #  Retrieve the MRS100 devices that are registered on this account
    await manager.async_device_discovery()
    roller_shutters = manager.find_devices(device_type="mrs100", online_status=OnlineStatus.ONLINE)
    if len(roller_shutters) < 1:
        print("No online MRS100 roller shutter timers found...")
    else:
        dev = roller_shutters[0]

        # Update device status: this is needed only the very first time we play with this device (or if the connection goes down)
        await dev.async_update()

        # Device found
        print(f"Roller Shutter Timer ({dev.type}): {dev.name}")

        # Open the roller shutter for 10s
        print(f"Opening {dev.name}...")
        await dev.async_open(channel=0)
        await asyncio.sleep(2)
        #Check status after 2s (Push notification)
        print(f"Opening... Status: {dev.get_status(channel=0)} - Position: {dev.get_position(channel=0)}")
        await asyncio.sleep(8)

        #Stop opening the roller shutter
        print(f"Stopping {dev.name}...")
        await dev.async_stop(channel=0)
        await asyncio.sleep(2)
        print(f"Stopping... Status: {dev.get_status(channel=0)} - Position: {dev.get_position(channel=0)}")
        
        await asyncio.sleep(5)
        
        #Close the roller shutter for 10s
        print(f"Closing {dev.name}...")
        await dev.async_close(channel=0)
        await asyncio.sleep(2)
        #Check status after 2s (Push notification)
        print(f"Closing... Status: {dev.get_status(channel=0)} - Position: {dev.get_position(channel=0)}")
        await asyncio.sleep(8)

        #Stop closing the roller shutter
        print(f"Stopping {dev.name}...")
        await dev.async_stop(channel=0)
        await asyncio.sleep(2)
        print(f"Stopping... Status: {dev.get_status(channel=0)} - Position: {dev.get_position(channel=0)}")

    # Close the manager and logout from http_api
    manager.close()
    await http_api_client.async_logout()

if __name__ == '__main__':
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    loop.stop()