from meross_iot.model.enums import DiffuserSprayMode
from meross_iot.model.enums import LightMode
import asyncio
import os

from meross_iot.controller.mixins.diffuser_spray import DiffuserSprayMixin
from meross_iot.controller.mixins.diffuser_light import DiffuserLightMixin
from meross_iot.http_api import MerossHttpClient
from meross_iot.manager import MerossManager
from meross_iot.model.enums import Namespace, OnlineStatus

EMAIL = os.environ.get('MEROSS_EMAIL') or "YOUR_MEROSS_CLOUD_EMAIL"
PASSWORD = os.environ.get('MEROSS_PASSWORD') or "YOUR_MEROSS_CLOUD_PASSWORD"


async def event_handler(namespace: Namespace, data: dict, device_internal_id: str, *args, **kwargs):
    print(f"An event occurred for device {device_internal_id}: {namespace}, Event data: {data}")


async def main():
    # Create the HTTP client API from user-password, setup the manager and start the discovery.
    http_api_client = await MerossHttpClient.async_from_user_password(email=EMAIL, password=PASSWORD, api_base_url="https://iot.meross.com")
    manager = MerossManager(http_client=http_api_client)
    await manager.async_device_discovery()

    # Find the mod150 oil diffuser device.
    # In our test, we are looking for a specific device, so we are not using the device_class parameter.
    devices = manager.find_devices(device_type="mod150", online_status=OnlineStatus.ONLINE)

    if len(devices) < 1:
        print("No online device found!")
    else:
        # Get the first online mod150 device we found.
        # We know that a mod150 implements both DiffuserLightMixin and DiffuserSprayMixin.
        dev: DiffuserLightMixin | DiffuserSprayMixin = devices[0]

        dev.register_push_notification_handler_coroutine(event_handler)

        # Let's update its status completely before working with it.
        await dev.async_update()

        # Put the light to RED and set diffuser to STRONG, then set it to BLUE and LIGHT, and finally to OFF
        # (both spray and light)
        print("Setting to RED and STRONG for 15 seconds.")
        await dev._async_diffuser_light_set_light_mode(mode=LightMode.MODE_RGB, onoff=True, rgb=(255, 0, 0))
        await dev.async_diffuser_spray_set_mode(mode=DiffuserSprayMode.STRONG)
        await asyncio.sleep(15)

        print("Setting to BLUE and LIGHT for 15 seconds.")
        await dev._async_diffuser_light_set_light_mode(mode=LightMode.MODE_RGB, rgb=(0, 0, 255))
        await dev.async_diffuser_spray_set_mode(mode=DiffuserSprayMode.LIGHT)
        await asyncio.sleep(15)

        print("Turning OFF.")
        await dev.async_diffuser_light_turn_off()
        await dev.async_diffuser_spray_set_mode(mode=DiffuserSprayMode.OFF)
        
        # Give time for push notifications
        print("Done.")

    # Close the manager and logout from http_api
    manager.close()
    await http_api_client.async_logout()


if __name__ == '__main__':
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    loop.stop()
