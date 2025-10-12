import asyncio
import os
from typing import List

from meross_iot.controller.subdevice_mixins.door_window import DoorWindowSensorMixin
from meross_iot.controller.subdevice_mixins.leakage_sensor import LeakageSensorMixin
from meross_iot.http_api import MerossHttpClient
from meross_iot.manager import MerossManager
from meross_iot.model.enums import Namespace, OnlineStatus

EMAIL = os.environ.get('MEROSS_EMAIL') or "YOUR_MEROSS_CLOUD_EMAIL"
PASSWORD = os.environ.get('MEROSS_PASSWORD') or "YOUR_MEROSS_CLOUD_PASSWORD"


async def doorwindow_event(namespace: str, data: dict, device_internal_id: str, *args, **kwargs):
    if namespace == Namespace.HUB_SENSOR_DOORWINDOW.value:
        print(f"Device {device_internal_id} - DOOR status -> {data}")
    else:
        print("An event has occurred, but that is not a door-window open/close state update")


async def main():
    # Set up the HTTP client API from user-password
    http_api_client = await MerossHttpClient.async_from_user_password(email=EMAIL, password=PASSWORD, api_base_url="https://iot.meross.com")

    # Setup and start the device manager
    manager = MerossManager(http_client=http_api_client)
    await manager.async_init()

    # Retrieve all the MS100 devices that are registered on this account
    await manager.async_device_discovery()

    # Retrieve door window sensors
    door_window_sensors: List[DoorWindowSensorMixin] = manager.find_devices(device_class=DoorWindowSensorMixin, online_status=OnlineStatus.ONLINE)

    if len(door_window_sensors) < 1:
        print("No online door-window sensors found!")
    else:
        # Let's register an event handle to quickly react in case of water leaks
        for sensor in door_window_sensors:
            sensor.register_push_notification_handler_coroutine(doorwindow_event)
            await sensor.async_update()

        # Manually force and update to retrieve the latest temperature sensed from
        # the device. This ensures we get the most recent data and not a cached value
        while True:
            try:
                for sensor in door_window_sensors:
                    await sensor.async_update()
                    print(f"Sensor {sensor.subdevice_id} -> Door/Window status={'OPEN' if sensor.door_window_opened else 'CLOSE'}")
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
