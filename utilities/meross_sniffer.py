import json
import logging
import ssl
import uuid as UUID
from hashlib import md5
from os import path, environ
from threading import Event
from zipfile import ZipFile

import paho.mqtt.client as mqtt

from meross_iot.cloud.client import build_client_request_topic
from meross_iot.cloud.device import AbstractMerossDevice
from meross_iot.logger import h, ROOT_MEROSS_LOGGER
from meross_iot.manager import MerossHttpClient
from meross_iot.manager import MerossManager

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

ROOT_MEROSS_LOGGER.removeHandler(h)


class DeviceSniffer(object):
    def __init__(self, user_id, hashed_password, target_device_uuid, ca_cert=None, domain="iot.meross.com", port=2001):
        self.connect_event = Event()
        self.subscribe_event = Event()

        self.domain = domain
        self.port = port
        self.target_device_uuid = target_device_uuid

        # Generate random app and client id
        md5_hash = md5()
        rnd_uuid = UUID.uuid4()
        md5_hash.update(("%s%s" % ("API", rnd_uuid)).encode("utf8"))
        self._app_id = md5_hash.hexdigest()
        self._client_id = 'app:%s' % md5_hash.hexdigest()

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
        self._mqtt_client.connect(self.domain, self.port, keepalive=30)

        # Starts a new thread that handles mqtt protocol and calls us back via callbacks
        l.debug("(Re)Starting the MQTT loop.")
        self._mqtt_client.loop_stop(True)
        self._mqtt_client.loop_start()
        self.connect_event.wait()

        # Subscribe to the corresponding topics ...
        topic = build_client_request_topic(self.target_device_uuid)
        self._mqtt_client.subscribe(topic)
        self.subscribe_event.wait()

    def stop(self):
        self._mqtt_client.disconnect()

    def _on_subscribe(self, client, userdata, mid, granted_qos):
        l.debug("Subscribed correctly")
        self.subscribe_event.set()

    def _on_message(self, client, userdata, msg):
        message = json.loads(str(msg.payload, "utf8"))
        header = message['header']
        l.info(message)

    def _on_disconnect(self, client, userdata, rc):
        l.debug("Disconnected from MQTT brocker")


def main():
    print("Welcome to the Sniffer utility. This python script will gather some useful information about your "
          "Meross devices. All the collected information will be zipped into a zip archive. "
          "You could share such zip file with the developers to help them add support for your device. "
          "Although this utility won't collect your email/password, we recommend you to change "
          "your Meross account password to a temporary one before using this software. Once you are done, "
          "you can restore back your original password. By doing so, you are 100% sure you are not leaking any "
          "real password to the developers.")
    email = environ.get("MEROSS_EMAIL")
    password = environ.get("MEROSS_PASSWORD")

    if email is None or password is None:
        email = input("Please specify your meross email: ")
        email = email.strip()
        password = input("Please specify your meross password: ")
        password = password.strip()

    devices = []
    http = None
    try:
        http = MerossHttpClient(email, password)
        print("# Collecting devices via HTTP api...")
        devices = http.list_devices()
        l.info("DEVICE LISTING VIA HTTP: %s" % devices)
    except:
        print("An error occurred while retrieving Meross devices.")
        exit(1)

    # If the login was successful, start the Meross Manager to "log" data
    manager = MerossManager(meross_email=email, meross_password=password)
    manager.start()

    print("# Listing ONLINE devices...")
    device_registry = {}
    for i, dev in enumerate(devices):
        if dev.get('onlineStatus') != 1:
            continue
        device_registry[str(i)] = dev
        print(f"{i}: {dev.get('devName')} ({dev.get('deviceType')})")

    if len(device_registry.keys())<1:
        print("No devices found or all devices are offline.")
        exit(0)

    while True:
        selection = input("Select the device you want to study: ")
        selection = selection.strip()
        selected_device = device_registry.get(selection)
        if selected_device is not None:
            break

    print("")
    print(f"You have selected {selected_device.get('devName')}.")

    # Start the manager
    creds = http.get_cloud_credentials()
    md5_hash = md5()
    clearpwd = "%s%s" % (creds.user_id, creds.key)
    md5_hash.update(clearpwd.encode("utf8"))
    hashed_password = md5_hash.hexdigest()
    sniffer = DeviceSniffer(
        creds.user_id,
        hashed_password,
        selected_device.get('uuid'),
        ca_cert=None,
        domain=selected_device.get('domain') or "iot.meross.com"
    )

    print("Starting the sniffer...")
    sniffer.start()
    print("You can now start commanding this device from the Meross APP. This utility will catch "
          "every command you send from the app to this device. Such data could help developers to "
          "reproduce the functionality on this library. When DONE, press ENTER to finish.")

    input("Press ENTER to finish.")
    sniffer.stop()

    # As very last step, try to collect data via get_all() and get_abilities
    print("Collecting state info...")
    try:
        d = manager.get_device_by_uuid(selected_device.get('uuid')) # type: AbstractMerossDevice
        sysdata = d.get_sys_data()
        abilities = d.get_abilities()
        l.info(f"Sysdata for {d.uuid}: {sysdata}")
        l.info(f"Abilities for {d.uuid}: {abilities}")
    except:
        l.exception(f"Could not collect sysdata/abilities for {selected_device.get('uuid')}")

    manager.stop()

    print("Collecting logs...")
    zipObj = ZipFile('data.zip', 'w')
    zipObj.write(SNIFF_LOG_FILE)
    zipObj.write(ROOT_LOG_FILE)
    zipObj.close()

    print("A zipfile has been created containing the logs collected during this execution. "
          "It is located in {path}.".format(path=path.abspath(zipObj.filename)))
    print("Thanks for helping the Meross community!")


if __name__ == '__main__':
    main()

