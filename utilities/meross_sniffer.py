import asyncio
import getpass
import json
import logging
import os
import ssl
import sys
import uuid as UUID
from hashlib import md5
from os import path, environ
from threading import Event
from zipfile import ZipFile
import paho.mqtt.client as mqtt
from meross_iot.http_api import MerossHttpClient
from meross_iot.manager import MerossManager
from meross_iot.model.enums import Namespace, OnlineStatus
from meross_iot.utilities.mqtt import build_device_request_topic, build_client_response_topic, build_client_user_topic


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


class DeviceSniffer(object):
    def __init__(self, user_id, hashed_password, target_device_uuid, ca_cert=None, mqtt_host="iot.meross.com", mqtt_port=2001):
        self.connect_event = Event()
        self.subscribe_event = Event()
        self.user_id = user_id

        self.device_topic = None
        self.client_response_topic = None
        self.user_topic = None

        self.mqtt_domain = mqtt_host
        self.mqtt_port = mqtt_port
        self.target_device_uuid = target_device_uuid

        # Generate random app and client id
        md5_hash = md5()
        rnd_uuid = UUID.uuid4()
        md5_hash.update(("%s%s" % ("API", rnd_uuid)).encode("utf8"))
        self._app_id = "sniffer"
        self._client_id = 'app:sniffer-%s' % md5_hash.hexdigest()

        self._mqtt_client = mqtt.Client(client_id=self._client_id,
                                        protocol=mqtt.MQTTv311)

        self._mqtt_client.on_connect = self._on_connect
        self._mqtt_client.on_message = self._on_message
        self._mqtt_client.on_disconnect = self._on_disconnect
        self._mqtt_client.on_subscribe = self._on_subscribe

        # Avoid login if user_id is None
        if user_id is not None:
            self._mqtt_client.username_pw_set(username=user_id,
                                              password=hashed_password)
        self._mqtt_client.tls_set(ca_certs=ca_cert, certfile=None,
                                  keyfile=None, cert_reqs=ssl.CERT_REQUIRED,
                                  tls_version=ssl.PROTOCOL_TLS,
                                  ciphers=None)

    def _on_connect(self, client, userdata, rc, other):
        l.debug("Connected to MQTT Broker")
        self.connect_event.set()

    def start(self):
        """
        Starts the connection to the MQTT broker
        :return:
        """
        l.debug("Initializing the MQTT connection...")
        self._mqtt_client.connect(self.mqtt_domain, self.mqtt_port, keepalive=30)

        # Starts a new thread that handles mqtt protocol and calls us back via callbacks
        l.debug("(Re)Starting the MQTT loop.")
        self._mqtt_client.loop_stop(True)
        self._mqtt_client.loop_start()
        self.connect_event.wait()

        # Subscribe to the corresponding topics ...
        self.device_topic = build_device_request_topic(self.target_device_uuid)
        self.client_response_topic = build_client_response_topic(self.user_id, self._app_id)
        self.user_topic = build_client_user_topic(self.user_id)

        l.info(f"Subscribing to topic: {self.device_topic}")
        self._mqtt_client.subscribe(self.device_topic)
        self.subscribe_event.wait()
        self.subscribe_event.clear()

        l.info(f"Subscribing to topic: {self.client_response_topic}")
        self._mqtt_client.subscribe(self.client_response_topic)
        self.subscribe_event.wait()
        self.subscribe_event.clear()

        l.info(f"Subscribing to topic: {self.user_topic}")
        self._mqtt_client.subscribe(self.user_topic)
        self.subscribe_event.wait()
        self.subscribe_event.clear()

    def stop(self):
        self._mqtt_client.disconnect()

    def _on_subscribe(self, client, userdata, mid, granted_qos):
        l.debug("Subscribed correctly")
        self.subscribe_event.set()

    def _on_message(self, client, userdata, msg):
        message = json.loads(str(msg.payload, "utf8"))
        header = message['header']

        topic_str = "Unknown"
        if msg.topic == self.user_topic:
            topic_str = "USER-TOPIC"
        elif msg.topic == self.client_response_topic:
            topic_str = "CLIENT-RESPONSE-TOPIC"
        elif msg.topic == self.device_topic:
            topic_str = "DEVICE-TOPIC"

        l.info("%s (%s) <- %s" % (topic_str, msg.topic, message))

    def _on_disconnect(self, client, userdata, rc):
        l.debug("Disconnected from MQTT brocker")


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

    # Start the manager
    creds = http.cloud_credentials
    md5_hash = md5()
    clearpwd = "%s%s" % (creds.user_id, creds.key)
    md5_hash.update(clearpwd.encode("utf8"))
    hashed_password = md5_hash.hexdigest()
    sniffer = DeviceSniffer(
        creds.user_id,
        hashed_password,
        selected_device.uuid,
        ca_cert=None,
        mqtt_host=selected_device.domain or "iot.meross.com"
    )

    print("Starting the sniffer...")
    sniffer.start()
    print("You can now start commanding this device from the Meross APP. This utility will catch "
          "every command you send from the app to this device. Such data could help developers to "
          "reproduce the functionality on this library. When DONE, press ENTER to finish.")

    input("Press ENTER to finish.")
    sniffer.stop()

    # As very last step, try to collect data via get_all() and get_abilities
    l.info("--------------- More data -----------------")
    print("Collecting state info...")
    manager = None
    try:
        manager = MerossManager(http_client=http)
        await manager.async_init()

        # Manually get device abilities
        response_all = await manager.async_execute_cmd(destination_device_uuid=selected_device.uuid,
                                                       method="GET",
                                                       namespace=Namespace.SYSTEM_ALL,
                                                       payload={},
                                                       mqtt_hostname=selected_device.mqtt_host,
                                                       mqtt_port=selected_device.mqtt_port)
        response_abilities = await manager.async_execute_cmd(destination_device_uuid=selected_device.uuid,
                                                             method="GET",
                                                             namespace=Namespace.SYSTEM_ABILITY,
                                                             payload={},
                                                             mqtt_hostname=selected_device.mqtt_host,
                                                             mqtt_port=selected_device.mqtt_port
                                                             )

        l.info(f"Sysdata for {selected_device.dev_name} ({selected_device.uuid}): {response_all}")
        l.info(f"Abilities for {selected_device.dev_name} ({selected_device.uuid}): {response_abilities}")
    except:
        l.exception(f"Could not collect sysdata/abilities for {selected_device.uuid}")
    finally:
        if manager is not None:
            manager.close()
        await http.async_logout()

    print("Collecting logs...")
    zipObj = ZipFile('data.zip', 'w')
    zipObj.write(SNIFF_LOG_FILE)
    zipObj.write(ROOT_LOG_FILE)
    zipObj.close()

    print("A zipfile has been created containing the logs collected during this execution. "
          "It is located in {path}.".format(path=path.abspath(zipObj.filename)))
    print("Thanks for helping the Meross community!")


def main():
    # On Windows + Python 3.8, you should uncomment the following
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    loop = asyncio.get_event_loop()
    loop.run_until_complete(_main())
    loop.close()


if __name__ == '__main__':
    main()
