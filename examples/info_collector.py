import asyncio
import json
import os
from typing import List

from meross_iot.controller.device import GenericSubDevice, BaseDevice
from meross_iot.controller.mixins.consumption import ConsumptionMixin, ConsumptionXMixin
from meross_iot.controller.mixins.diffuser_light import DiffuserLightMixin
from meross_iot.controller.mixins.diffuser_spray import DiffuserSprayMixin
from meross_iot.controller.mixins.dnd import SystemDndMixin
from meross_iot.controller.mixins.electricity import ElectricityMixin
from meross_iot.controller.mixins.hub import HubMixin
from meross_iot.controller.subdevice_mixins.leakage_sensor import LeakageSensorMixin
from meross_iot.http_api import MerossHttpClient
from meross_iot.manager import MerossManager
from meross_iot.model.enums import Namespace, OnlineStatus, DiffuserLightMode

EMAIL = os.environ.get('MEROSS_EMAIL') or "YOUR_MEROSS_CLOUD_EMAIL"
PASSWORD = os.environ.get('MEROSS_PASSWORD') or "YOUR_MEROSS_CLOUD_PASSWORD"

_DEVICE_CLASS=BaseDevice


async def event_handler(namespace: Namespace, data: dict, device_internal_id: str, *args, **kwargs):
    print(f"An event occurred for device {device_internal_id}: {namespace}, Event data: {data}")


async def main():
    # Set up the HTTP client API from user-password
    http_api_client = await MerossHttpClient.async_from_user_password(email=EMAIL, password=PASSWORD, api_base_url="https://iot.meross.com")

    # Setup and start the device manager
    manager = MerossManager(http_client=http_api_client)

    # Discover devices and subdevices
    await manager.async_device_discovery()

    # Filter the device we want to use
    #devices = manager.find_devices(device_class=_DEVICE_CLASS, online_status=OnlineStatus.ONLINE)
    devices = manager.find_devices(device_type="msg200", online_status=OnlineStatus.ONLINE)

    if len(devices) < 1:
        print("No online device found!")
    else:
        # Get the first device
        dev: BaseDevice = devices[0]
        dev.register_push_notification_handler_coroutine(event_handler)
        await dev.async_update()

        # res = await dev._execute_command(method='GET'
        #                             namespace=Namespace.DIFFUSER_LIGHT,
        #                             payload=payload)
        #print(res)

        # Trigger the SYSTEM_ALL update
        update_data = await dev._execute_command('GET', Namespace.SYSTEM_ALL, {})

        update_data['all']['system']['hardware']['uuid'] = "${UUID}"
        update_data['all']['system']['hardware']['macAddress'] = "${MAC_ADDRESS}"
        update_data['all']['system']['firmware']['wifiMac'] = "${WIFI_MAC}"
        update_data['all']['system']['firmware']['userId'] = "${USER_ID}"
        update_data['all']['system']['firmware']['innerIp'] = "${INNER_IP}"

        data = json.dumps(update_data)
        print(json.dumps(update_data))

        # Specific method testing
        #method_response = await dev._execute_command('GET', Namespace.CONTROL_ELECTRICITY, {})

        method_response = await dev._execute_command('GET', Namespace.GARAGE_DOOR_MULTIPLECONFIG,{})
        print(json.dumps(method_response))

        method_response = await dev._execute_command('SET', Namespace.GARAGE_DOOR_MULTIPLECONFIG, {'config': {"channel":2,"doorEnable":1}})
        print(json.dumps(method_response))

        method_response = await dev._execute_command('SET', Namespace.GARAGE_DOOR_STATE, {"state": {"channel": 2, "open": 1}})
        print(json.dumps(method_response))
        await asyncio.sleep(10)
        method_response = await dev._execute_command('SET', Namespace.GARAGE_DOOR_STATE,
                                                     {"state": {"channel": 2, "open": 0}})
        print(json.dumps(method_response))

        await asyncio.sleep(10)
        method_response = await dev._execute_command('GET', Namespace.GARAGE_DOOR_STATE, {"state": {}})
        print(json.dumps(method_response))

        # Give time for push notifications
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
