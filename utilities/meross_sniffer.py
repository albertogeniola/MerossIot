import asyncio
import datetime
import getpass
import json
import logging
import os
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from hashlib import md5
from os import path, environ
from typing import List, Dict, Tuple
from zipfile import ZipFile


from meross_iot.http_api import MerossHttpClient
from meross_iot.manager import MerossManager, TransportMode
from meross_iot.model.credentials import MerossCloudCreds
from meross_iot.model.enums import Namespace, OnlineStatus
from meross_iot.model.http.device import HttpDeviceInfo
from utilities.meross_fake_app import AppSniffer
from utilities.meross_fake_device import FakeDeviceSniffer
from urllib.parse import urlparse

SNIFF_LOG_FILE = 'sniff.log'
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Configure logging
logging.basicConfig(level=logging.DEBUG)
l = logging.getLogger()
l.handlers.clear()

# Debug file handler
file_handler = logging.FileHandler(filename='sniff.log', mode='w+')
file_handler.setFormatter(formatter)
file_handler.setLevel(logging.DEBUG)
l.addHandler(file_handler)

stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)
stream_handler.setLevel(logging.CRITICAL)
l.addHandler(stream_handler)


def _print_welcom_message():
    print("Welcome to the Sniffer utility. This python script will gather some useful information about your "
          "Meross devices. All the collected information will be zipped into a zip archive. "
          "You could share such zip file with the developers to help them add support for your device. "
          "Although this utility won't collect your email/password, we recommend you to change "
          "your Meross account password to a temporary one before using this software. Once you are done, "
          "you can restore back your original password. By doing so, you are 100% sure you are not leaking any "
          "real password to the developers.\n\n"
          "ATTENTION: The sniffer does not support MFA login. Please disable MFA if willing to use this script.\n\n")


async def _async_gather_http_client() -> MerossHttpClient:
    api_base_url = environ.get("MEROSS_API_URL", "https://iotx-us.meross.com")
    if api_base_url is None:
        api_base_url = input("Please specify the meross API base url. It should be 'https://iotx-us.meross.com' or 'https://iotx-eu.meross.com' or 'https://iotx-ap.meross.com'. "
                             "Leave blank if unsure: ")
        api_base_url = api_base_url.strip()
        if api_base_url is None:
            api_base_url = "https://iotx-us.meross.com"
            print(f"Assuming API Base URL: {api_base_url}")
        try:
            urlparse(api_base_url)
        except:
            print("Invalid API/URL provided.")
            exit(2)
    email = environ.get("MEROSS_EMAIL")
    if email is None:
        email = input("Please specify your meross email: ")
        email = email.strip()

    password = environ.get("MEROSS_PASSWORD")
    if password is None:
        password = getpass.getpass(prompt='Please specify your Meross password: ', stream=sys.stdout).strip()
    try:
        return await MerossHttpClient.async_from_user_password(api_base_url=api_base_url, email=email, password=password)
    except Exception:
        print("An error occurred while gathering MerossAPI Client. Make sure your email-password credentials are valid.")
        exit(1)


async def _async_print_device_list(client: MerossHttpClient) -> List[HttpDeviceInfo]:
    # Gather HTTP devices
    try:
        print("# Collecting devices via HTTP api...")
        devices = await client.async_list_devices()
        for i, d in enumerate(devices):
            print(f"[{i}] - {d.dev_name} ({d.device_type}) - {d.online_status.name}")
        return devices
    except:
        print("An error occurred while retrieving Meross devices.")
        exit(1)


async def _async_select_device(devices: List[HttpDeviceInfo]) -> HttpDeviceInfo:
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
    return selected_device


async def _async_collect_device_base_data(client: MerossHttpClient, selected_device: HttpDeviceInfo) -> Tuple[Dict, MerossManager]:
    print("Collecting devices info...")
    manager = MerossManager(http_client=client)
    await manager.async_init()
    mqtt_host = selected_device.get_mqtt_host()
    mqtt_port = selected_device.get_mqtt_port()

    # Manually get device abilities
    print(f"Collecting {Namespace.SYSTEM_ALL} info...")
    system_data = await manager.async_execute_cmd(destination_device_uuid=selected_device.uuid,
                                                   method="GET",
                                                   namespace=Namespace.SYSTEM_ALL,
                                                   payload={},
                                                   mqtt_hostname=mqtt_host,
                                                   mqtt_port=mqtt_port)
    l.info(f"Sysdata for {selected_device.dev_name} ({selected_device.uuid}): {system_data}")

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

    return system_data, manager


async def _async_start_fake_device_sniffer(cloud_credentials: MerossCloudCreds, selected_device: HttpDeviceInfo, mac_address: str) -> FakeDeviceSniffer:
    print("Starting the fake device emulator...")
    fake_device_sniffer = FakeDeviceSniffer(uuid=selected_device.uuid, mac_address=mac_address,
                                            meross_user_id=cloud_credentials.user_id,
                                            meross_cloud_key=cloud_credentials.key,
                                            mqtt_host=selected_device.get_mqtt_host(),
                                            mqtt_port=selected_device.get_mqtt_port(),
                                            logger=l)
    await fake_device_sniffer.async_start(timeout=5.0)
    return fake_device_sniffer


def _start_app_sniffer(cloud_credentials: MerossCloudCreds, selected_device: HttpDeviceInfo) -> AppSniffer:
    md5_hash = md5()
    clearpwd = "%s%s" % (cloud_credentials.user_id, cloud_credentials.key)
    md5_hash.update(clearpwd.encode("utf8"))
    hashed_password = md5_hash.hexdigest()
    app_sniffer = AppSniffer(
        l,
        cloud_credentials.user_id,
        hashed_password,
        selected_device.uuid,
        ca_cert=None,
        mqtt_host=selected_device.get_mqtt_host(),
        mqtt_port=selected_device.get_mqtt_port()
    )

    print("Starting the app-simulator sniffer...")
    app_sniffer.start()
    return app_sniffer


async def _async_sniff(device_sniffer: FakeDeviceSniffer, zip_obj: ZipFile, meross_manager: MerossManager, selected_device: HttpDeviceInfo):
    print("--------------------------------------\n"
          "PHASE 1: intercepting device commands.\n"
          "--------------------------------------\n"
          "The goal of this phase is to 'intercept' the commands that the APP sends to the device, pretending to"
          "be that specific device. In other words, we will 'spoof' the device connection so that the commands "
          "sent by the official APP are instead routed to this utility.\n\n"
          "To do so, you need to disconnect the real device from the 'power outlet', so that it gets cut out from "
          "the Meross cloud, then issue the command you want to inspect from the Meross App. This command will FAIL,"
          "as the message will not reach the real Meross Device, but this utility instead. When the command is "
          "received, it will be printed out.\n"
          "If you need to test multiple states/commands, you can always re-attach the power to the real Meross device,"
          "perform adjust its original state and then cut off the power and issue the command you want to get info.\n"
          "To simplify this process, the utility will guide you throughout the process.\n"
          "\nXXXXXXXXXXXXXX ATTENTION XXXXXXXXXXXXXX\n"
          "XXX MAKE SURE THE APP IS NOT CONNECTED TO THE SAME WIFI OF THE MEROSS DEVICE."
          "XXX If both the APP and the Meross device are on the same WiFi network, their communication will not "
          "XXX be intercepted. So, it's BETTER to disable the WiFi completely on the smartphone and rely on 3g/4g/5g "
          "XXX connectivity. That will make sure the APP uses the MQTT channel to talk to the device, and so the "
          "XXX communication will be intercepted by this sniffer."
          "\nXXXXXXXXXXXXXX ATTENTION XXXXXXXXXXXXXX\n\n"
          )

    messages = set()
    executor = ThreadPoolExecutor(2)

    with tempfile.NamedTemporaryFile(mode="w+t", encoding="utf8", prefix=f"sniffed_commands", suffix=".txt", delete=False) as f:
        residual_timeout = 30.0
        print(f"Waiting up to 30 seconds for messages...")
        while True:
            try:
                before = datetime.datetime.now().timestamp()
                raw_message, namespace, method, payload = await asyncio.wait_for(device_sniffer.async_wait_for_message(), timeout=residual_timeout)
                after = datetime.datetime.now().timestamp()
                key = f"{method}{namespace}{payload}"
                if key in messages:
                    # This message type was already intercepted
                    residual_timeout -= (after - before)
                    if residual_timeout > 0:
                        continue
                    else:
                        raise TimeoutError()
            except asyncio.exceptions.TimeoutError:
                resp = input("Timeout: no message received. Do you want to wait more? [y/N]:").strip().lower()
                if resp in ('y','yes'):
                    residual_timeout = 30
                    print(f"Waiting up to 30 seconds for messages...")
                    continue
                else:
                    break

            messages.add(key)
            print(f"New message type received: {method} {namespace}: {payload}")
            note = input("Describe the command you issued on the APP which caused this message. If unsure, just type \"?\" or \"IDK\": ")
            f.write(f"\n\nCommand Description: {note}\n\n")
            f.write(f"Request: \n")
            f.write(raw_message.payload.decode('utf8'))
            f.flush()

            # Attempt now to retrieve a response simulating that command to the real device
            print("Replicating the same message to the device in order to catch the real response...")
            try:
                response = await meross_manager.async_execute_cmd(
                    mqtt_hostname=selected_device.get_mqtt_host(),
                    mqtt_port=selected_device.get_mqtt_port(),
                    destination_device_uuid=selected_device.uuid,
                    method=method,
                    namespace=namespace,
                    payload=payload,
                    timeout=5.0,
                    override_transport_mode=TransportMode.MQTT_ONLY
                )
                f.write(f"\nResponse: \n")
                f.write(json.dumps(response))
            except Exception as e:
                l.exception("An error occurred while collecting a response from the device simulating the latest message. No response will be catched.")
                print("Skipping response collection.")
            print(f"Waiting up to 30 seconds for messages...")
        zip_obj.write(f.name, f"sniffed_commands.txt")


async def _main():
    zip_obj = ZipFile('data.zip', 'w')
    _print_welcom_message()
    client = await _async_gather_http_client()
    manager = None
    try:
        devices = await _async_print_device_list(client)
        selected_device = await _async_select_device(devices)

        # Log/Collect device data device data
        system_data, manager = await _async_collect_device_base_data(client, selected_device)
        device_mac_address = system_data["all"]["system"]["hardware"]["macAddress"]

        # Start the device sniffer
        device_sniffer = await _async_start_fake_device_sniffer(client.cloud_credentials, selected_device, device_mac_address)

        # Start the app sniffer
        app_sniffer = _start_app_sniffer(client.cloud_credentials, selected_device)

        # Start simulation and sniffing (phase 1)
        await _async_sniff(device_sniffer, zip_obj, manager, selected_device)
        await device_sniffer.async_stop()
        # Start the PUSH notification catching (phase 2)
        app_sniffer.stop()

    finally:
        if client is not None:
            await client.async_logout()
        if manager is not None:
            manager.close()

        print("Collecting logs...")
        zip_obj.write(SNIFF_LOG_FILE, 'sniff_log.txt')
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
