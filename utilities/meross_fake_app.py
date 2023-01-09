import asyncio
import json
from hashlib import md5
from typing import Dict
from uuid import uuid4
from threading import Event
from paho.mqtt import client as mqtt

from paho.mqtt.client import ssl, MQTTMessage

from meross_iot.utilities.mqtt import build_device_request_topic, build_client_response_topic, build_client_user_topic
from utilities.mixedqueue import MixedQueue


class AppSniffer(object):
    def __init__(self, logger, user_id, hashed_password, target_device_uuid, ca_cert=None, mqtt_host="iot.meross.com", mqtt_port=2001):
        self.l = logger
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
        rnd_uuid = uuid4()
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
                                  tls_version=ssl.PROTOCOL_TLS_CLIENT,
                                  ciphers=None)

        self._push_queue = MixedQueue(asyncio.get_running_loop())

    def _on_connect(self, client, userdata, rc, other):
        self.l.debug("Connected to MQTT Broker")
        self.connect_event.set()

    def start(self):
        """
        Starts the connection to the MQTT broker
        :return:
        """
        self.l.debug("Initializing the MQTT connection...")
        self._mqtt_client.connect(self.mqtt_domain, self.mqtt_port, keepalive=30)

        # Starts a new thread that handles mqtt protocol and calls us back via callbacks
        self.l.debug("(Re)Starting the MQTT loop.")
        self._mqtt_client.loop_stop(force=True)
        self._mqtt_client.loop_start()
        self.connect_event.wait()

        # Subscribe to the corresponding topics ...
        self.device_topic = build_device_request_topic(self.target_device_uuid)
        self.client_response_topic = build_client_response_topic(self.user_id, self._app_id)
        self.user_topic = build_client_user_topic(self.user_id)

        self.l.info(f"Subscribing to topic: {self.device_topic}")
        self._mqtt_client.subscribe(self.device_topic)
        self.subscribe_event.wait()
        self.subscribe_event.clear()

        self.l.info(f"Subscribing to topic: {self.client_response_topic}")
        self._mqtt_client.subscribe(self.client_response_topic)
        self.subscribe_event.wait()
        self.subscribe_event.clear()

        self.l.info(f"Subscribing to topic: {self.user_topic}")
        self._mqtt_client.subscribe(self.user_topic)
        self.subscribe_event.wait()
        self.subscribe_event.clear()

    def stop(self):
        self._mqtt_client.disconnect()
        self._mqtt_client.loop_stop(force=True)

    def _on_subscribe(self, client, userdata, mid, granted_qos):
        self.l.debug("Subscribed correctly")
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

        self.l.info("%s (%s) <- %s" % (topic_str, msg.topic, message))
        if header['method'].upper() == 'PUSH':
            self._push_queue.sync_put(message)

    def _on_disconnect(self, client, userdata, rc):
        self.l.debug("Disconnected from MQTT broker")

    async def async_wait_push_notification(self) -> Dict:
        return await self._push_queue.async_get()
