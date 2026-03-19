import asyncio
import os
from typing import List

from meross_iot.controller.subdevice import Ms200Sensor
from meross_iot.http_api import MerossHttpClient
from meross_iot.manager import MerossManager
from meross_iot.model.enums import Namespace, OnlineStatus

EMAIL = os.environ.get('MEROSS_EMAIL') or "YOUR_MEROSS_CLOUD_EMAIL"
PASSWORD = os.environ.get('MEROSS_PASSWORD') or "YOUR_MEROSS_CLOUD_PASSWORD"
API_URL = "https://iot.meross.com"

async def opening_event(namespace: Namespace, data: dict, device_internal_id: str, *args, **kwargs):
    print("An event has occurred!")
    if namespace == Namespace.CONTROL_ALARM:
        print(f"Alarm occurred! Event data: {data}")
    elif namespace == Namespace.HUB_SENSOR_DOORWINDOW:
        print(f"opening occurred! Event data: {data}")
    else:
        print(f"Another event occurred: {namespace.value}, Event data: {data}")


async def main():
    # Setup the HTTP client API from user-password
    http_api_client = await MerossHttpClient.async_from_user_password(email=EMAIL, password=PASSWORD, api_base_url=API_URL)

    # Setup and start the device manager
    manager = MerossManager(http_client=http_api_client)
    await manager.async_init()

    # Retrieve all the MS200 devices that are registered on this account
    await manager.async_device_discovery()

    # Retrieve door/window sensors : ms200
    door_window_sensors: List[Ms200Sensor] = manager.find_devices(device_class=Ms200Sensor, online_status=OnlineStatus.ONLINE)

    if len(door_window_sensors) < 1:
        print("No online door window sensors found!")
    else:
        # Let's register an event handle to quickly react in case of opening
        for sensor in door_window_sensors:
            sensor.register_push_notification_handler_coroutine(opening_event)

        # Manually force and update to retrieve the latest event from
        # the device. This ensures we get the most recent data and not a cached value
        while True:
            try:
                for sensor in door_window_sensors:
                    print(f"Sensor {sensor.name} - Current open status = {sensor.is_opened}. "
                          f"Is currently opened? {sensor.is_opened}. "
                          f"Last timestamp of opening = {sensor.latest_detected_opening_ts if sensor.latest_detected_opening_ts is not None else 'NEVER'}")
                    print("Press CTRL+C to terminate.")
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
