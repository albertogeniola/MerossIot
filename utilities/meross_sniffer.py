import asyncio
import getpass
import logging
import os
import sys
from hashlib import md5
from os import path, environ
from zipfile import ZipFile

from meross_iot.http_api import MerossHttpClient
from meross_iot.manager import MerossManager
from meross_iot.model.enums import Namespace, OnlineStatus
from meross_iot.utilities.network import extract_domain
from utilities.meross_fake_app import AppSniffer
from utilities.meross_fake_device import FakeDeviceSniffer

SNIFF_LOG_FILE = 'sniff.log'
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
l = logging.getLogger().getChild("Sniffer")
l.setLevel(logging.DEBUG)
lhandler = logging.FileHandler(mode='w', filename=SNIFF_LOG_FILE)
lhandler.setFormatter(formatter)
l.addHandler(lhandler)

ROOT_LOG_FILE = 'root.log'
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
r = logging.getLogger()
r.setLevel(logging.DEBUG)
rhandler = logging.FileHandler(mode='w', filename=ROOT_LOG_FILE)
rhandler.setFormatter(formatter)
r.addHandler(rhandler)
r.setLevel(logging.DEBUG)


async def _main():
    print("Welcome to the Sniffer utility. This python script will gather some useful information about your "
          "Meross devices. All the collected information will be zipped into a zip archive. "
          "You could share such zip file with the developers to help them add support for your device. "
          "Although this utility won't collect your email/password, we recommend you to change "
          "your Meross account password to a temporary one before using this software. Once you are done, "
          "you can restore back your original password. By doing so, you are 100% sure you are not leaking any "
          "real password to the developers.")
    email = environ.get("MEROSS_EMAIL")
    if email is None:
        email = input("Please specify your meross email: ")
        email = email.strip()

    password = environ.get("MEROSS_PASSWORD")
    if password is None:
        password = getpass.getpass(prompt='Please specify your Meross password: ', stream=sys.stdout).strip()

    devices = []
    http = None

    # Gather HTTP devices
    try:
        http = await MerossHttpClient.async_from_user_password(email, password)
        print("# Collecting devices via HTTP api...")
        devices = await http.async_list_devices()
    except:
        print("An error occurred while retrieving Meross devices.")
        exit(1)

    for i, d in enumerate(devices):
        print(f"[{i}] - {d.dev_name} ({d.device_type}) - {d.online_status.name}")

    print("Please note that some devices rely on a HUB. Those devices won't be listed: in such cases, you need"
          "to select the corresponding HUB device.")

    while True:
        selection = input("Select the device you want to study (numeric index): ")
        selection = int(selection.strip())
        selected_device = devices[selection]
        if selected_device is not None:
            break

    print(f"You have selected {selected_device.dev_name}.")
    if selected_device.online_status != OnlineStatus.ONLINE:
        print("!! WARNING !! You selected a device that has not been reported as online. ")

    # Retrieve device data
    print("Collecting devices info...")
    manager = MerossManager(http_client=http)
    await manager.async_init()
    mqtt_host = selected_device.get_mqtt_host()
    mqtt_port = selected_device.get_mqtt_port()

    # Manually get device abilities
    print(f"Collecting {Namespace.SYSTEM_ALL} info...")
    response_all = await manager.async_execute_cmd(destination_device_uuid=selected_device.uuid,
                                                   method="GET",
                                                   namespace=Namespace.SYSTEM_ALL,
                                                   payload={},
                                                   mqtt_hostname=mqtt_host,
                                                   mqtt_port=mqtt_port)
    l.info(f"Sysdata for {selected_device.dev_name} ({selected_device.uuid}): {response_all}")

    try:
        print(f"Collecting {Namespace.SYSTEM_ABILITY} info...")
        response_abilities = await manager.async_execute_cmd(destination_device_uuid=selected_device.uuid,
                                                             method="GET",
                                                             namespace=Namespace.SYSTEM_ABILITY,
                                                             payload={},
                                                             mqtt_hostname=mqtt_host,
                                                             mqtt_port=mqtt_port
                                                             )

        l.info(f"Abilities for {selected_device.dev_name} ({selected_device.uuid}): {response_abilities}")
    except:
        l.exception(f"Could not collect sysdata/abilities for {selected_device.uuid}")

    # Close the manager as we won't need it any longer
    if manager is not None:
        manager.close()

    # Start the device sniffer
    fake_device = FakeDeviceSniffer(uuid=selected_device.uuid, mac_address=, meross_user_id=,meross_cloud_key=,)

    # Start the app-sniffer manager
    creds = http.cloud_credentials
    md5_hash = md5()
    clearpwd = "%s%s" % (creds.user_id, creds.key)
    md5_hash.update(clearpwd.encode("utf8"))
    hashed_password = md5_hash.hexdigest()
    app_sniffer = AppSniffer(
        l,
        creds.user_id,
        hashed_password,
        selected_device.uuid,
        ca_cert=None,
        mqtt_host=extract_domain(selected_device.domain) or "iot.meross.com"
    )

    print("Starting the app-simulator sniffer...")
    app_sniffer.start()
    print("PHASE 1: device abilities, system info and push notifications.\n"
          "Please start manipulating the physical device. If the device has buttons, press them.\n"
          "If the device has sensors, make sure to activate some sensors state change (in case of power "
          "meters, connect a load).\n"
          "You can also issue commands via the Meross Official App, so that the utility catches the"
          "push notifications, if any is generated.\n\n")

    input("Waiting for you to perform actions on the device.\n"
          "When DONE, press ENTER to proceed to PHASE2.\n")
    app_sniffer.stop()

    # Start the Phase 2
    print("Allocating device sniffer...")

    print("PHASE 2: device commands.\n"
          "It's now time to 'collect' the commands as they are received from the device.\n"
          "Please send commands from the Meross App to the target device.\n"
          "Most probably, the device will not answer correctly and the App will report errors.\n"
          "That's fine, just ignore them and keep issuing different commands to the device.\n\n")

    # Invalidate the HTTP token
    await http.async_logout()

    print("Collecting logs...")
    zip_obj = ZipFile('data.zip', 'w')
    zip_obj.write(SNIFF_LOG_FILE)
    zip_obj.write(ROOT_LOG_FILE)
    zip_obj.close()

    print("A zipfile has been created containing the logs collected during this execution. "
          "It is located in {path}.".format(path=path.abspath(zip_obj.filename)))
    print("Thanks for helping the Meross community!")


def main():
    # On Windows + Python 3.8, you should uncomment the following
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    loop = asyncio.get_event_loop()
    loop.run_until_complete(_main())
    loop.stop()


if __name__ == '__main__':
    main()
