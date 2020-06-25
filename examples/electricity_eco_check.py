import asyncio
import os
import time
from meross_iot.controller.mixins.electricity import ElectricityMixin
from meross_iot.controller.mixins.garage import GarageOpenerMixin
from meross_iot.http_api import MerossHttpClient
from meross_iot.manager import MerossManager

EMAIL = os.environ.get('MEROSS_EMAIL') or "YOUR_MEROSS_CLOUD_EMAIL"
PASSWORD = os.environ.get('MEROSS_PASSWORD') or "YOUR_MEROSS_CLOUD_PASSWORD"


async def get_metric(dev):
    i = 0
    list_power = []
    print("while time 60 secondes check if < 30Watt consumming down...")
    while i < 60:
        instant_consumption = await dev.async_get_instant_metrics()
        power = instant_consumption.power
        #print("uuid : {} \n Watt : {} 100%".format(plugs.uuid, (power+current)/1000))
        list_power.append(power)
        i = i + 1
        time.sleep(1)

    avg = sum(list_power)/len(list_power)

    if avg < 20.0 and avg > 0.0 and max(list_power) < 20.0:
        print(avg, "turn off")
        await dev.async_turn_off(channel=0)

    print(f"Current consumption data: {instant_consumption}")

async def sub_element_electric(devs):
    tasks = []
    sem = asyncio.Semaphore(400)

    for dev in devs:
        task = asyncio.ensure_future(get_metric(dev))
        tasks.append(task)

    r = await asyncio.gather(*tasks)
    return r

async def main():
    # Setup the HTTP client API from user-password
    http_api_client = await MerossHttpClient.async_from_user_password(email=EMAIL, password=PASSWORD)

    # Setup and start the device manager
    manager = MerossManager(http_client=http_api_client)
    await manager.async_init()

    # Retrieve all the devices that implement the electricity mixin
    await manager.async_device_discovery()
    # device_class=ElectricityMixin
    devs = manager.find_devices(device_type="mss310")

    if len(devs) < 1:
        print("No electricity-capable device found...")
    else:
        # Read the electricity power/voltage/current
        images = await sub_element_electric(devs)
        #sub_run(dev)

    # Close the manager and logout from http_api
    manager.close()
    await http_api_client.async_logout()

if __name__ == '__main__':
    # On Windows + Python 3.8, you should uncomment the following
    # asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    loop.close()
