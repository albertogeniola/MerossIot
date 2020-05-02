import asyncio
import copy
import json
import random
import socket
import ssl
import string
import time
import uuid as UUID
from asyncio import Future
from hashlib import md5
from typing import Optional
import logging
import paho.mqtt.client as mqtt

from meross_iot.credentials import MerossCloudCreds
from meross_iot.cloud.exception import UnconnectedError
from meross_iot.model.enums import Namespace
from meross_iot.model.push.factory import parse_push_notification
from meross_iot.model.push.generic import GenericPushNotification

logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.DEBUG)
l = logging.getLogger(__name__)


def build_device_request_topic(client_uuid: str) -> str:
    """
    Builds the MQTT topic where commands should be send to specific devices
    :param client_uuid:
    :return:
    """
    return f"/appliance/{client_uuid}/subscribe"


def build_client_response_topic(user_id: str, app_id: str) -> str:
    """
    Builds the MQTT topic where the device sends back ACKs to commands
    :param app_id:
    :param user_id:
    :param client_uuid:
    :return:
    """
    return f"/app/{user_id}-{app_id}/subscribe"


def build_client_user_topic(user_id: str):
    """
    Builds the topic name where user push notification are received
    :param user_id:
    :return:
    """
    return f"/app/{user_id}/subscribe"


def device_uuid_from_push_notification(from_topic: str):
    """
    Extracts the device uuid from the "from" header of the received messages.
    :param from_topic:
    :return:
    """
    return from_topic.split('/')[1]


class MerossMqttClient(object):
    """
    This class handles MQTT exchange with Meross MQTT broker.
    """

    def __init__(self,
                 cloud_credentials: MerossCloudCreds,
                 auto_reconnect: Optional[bool] = True,
                 domain: Optional[str] = "iot.meross.com",
                 port: Optional[int] = 2001,
                 ca_cert: Optional[str] = None,
                 *args,
                 **kwords) -> None:

        # Store local attributes
        self._cloud_creds = cloud_credentials
        self._auto_reconnect = auto_reconnect
        self._domain = domain
        self._port = port
        self._ca_cert = ca_cert
        self._app_id, self._client_id = _generate_client_and_app_id()
        self._pending_messages_futures = {}

        # Setup mqtt client
        mqtt_pass = _generate_mqtt_password(user_id=self._cloud_creds.user_id, key=self._cloud_creds.key)
        self._mqtt_client = mqtt.Client(client_id=self._client_id, protocol=mqtt.MQTTv311)
        self._mqtt_client.on_connect = self._on_connect
        self._mqtt_client.on_message = self._on_message
        self._mqtt_client.on_disconnect = self._on_disconnect
        self._mqtt_client.on_subscribe = self._on_subscribe
        self._mqtt_client.username_pw_set(username=self._cloud_creds.user_id, password=mqtt_pass)
        self._mqtt_client.tls_set(ca_certs=self._ca_cert, certfile=None,
                                  keyfile=None, cert_reqs=ssl.CERT_REQUIRED,
                                  tls_version=ssl.PROTOCOL_TLS,
                                  ciphers=None)

        # Setup synchronization primitives
        self._loop = asyncio.get_event_loop()
        self._mqtt_connected_and_subscribed = asyncio.Event()

        # Prepare MQTT topic names
        self._client_response_topic = build_client_response_topic(user_id=self._cloud_creds.user_id,
                                                                  app_id=self._app_id)
        self._user_topic = build_client_user_topic(user_id=self._cloud_creds.user_id)

    def close(self):
        l.info("Disconnecting from mqtt")
        self._mqtt_client.disconnect()
        l.debug("Stopping the MQTT looper.")
        self._mqtt_client.loop_stop(True)
        l.info("MQTT Client has fully disconnected.")

    async def async_init(self) -> None:
        """
        Connects to the remote MQTT broker and subscribes to the relevant topics.
        :return:
        """
        l.info("Initializing the MQTT connection...")
        self._mqtt_client.connect(host=self._domain, port=self._port, keepalive=30)

        # Starts a new thread that handles mqtt protocol and calls us back via callbacks
        l.debug("Starting the MQTT looper.")
        self._mqtt_client.loop_start()

        # Wait until the client connects and subscribes to the broken
        await self._mqtt_connected_and_subscribed.wait()
        self._mqtt_connected_and_subscribed.clear()
        l.debug("Connected and subscribed to relevant topics")

    def _on_connect(self, client, userdata, rc, other):
        # NOTE! This method is called by the paho-mqtt thread, thus any invocation to the
        # asyncio platform must be scheduled via `self._loop.call_soon_threadsafe()` method.

        l.debug(f"Connected with result code {rc}")
        # Subscribe to the relevant topics
        l.debug("Subscribing to topics...")
        client.subscribe([(self._user_topic, 0), (self._client_response_topic, 0)])

    def _on_disconnect(self, client, userdata, rc):
        # NOTE! This method is called by the paho-mqtt thread, thus any invocation to the
        # asyncio platform must be scheduled via `self._loop.call_soon_threadsafe()` method.

        l.info("Disconnection detected. Reason: %s" % str(rc))

        # If the client disconnected explicitly, the mqtt library handles thred stop autonomously
        if rc == mqtt.MQTT_ERR_SUCCESS:
            pass
        else:
            # Otherwise, if the disconnection was not intentional, we probably had a connection drop.
            # In this case, we only stop the loop thread if auto_reconnect is not set. In fact, the loop will
            # handle reconnection autonomously on connection drops.
            if not self._auto_reconnect:
                l.info("Stopping mqtt loop on connection drop")
                client.loop_stop(True)
            else:
                l.warning("Client has been disconnected, however auto_reconnect flag is set. "
                          "Won't stop the looping thread, as it will retry to connect.")

    def _on_unsubscribe(self):
        # NOTE! This method is called by the paho-mqtt thread, thus any invocation to the
        # asyncio platform must be scheduled via `self._loop.call_soon_threadsafe()` method.
        l.debug("Unsubscribed from topics")

    def _on_subscribe(self, client, userdata, mid, granted_qos):
        # NOTE! This method is called by the paho-mqtt thread, thus any invocation to the
        # asyncio platform must be scheduled via `self._loop.call_soon_threadsafe()` method.
        l.debug("Succesfully subscribed to topics.")
        self._loop.call_soon_threadsafe(
            self._mqtt_connected_and_subscribed.set
        )

    def _on_message(self, client, userdata, msg):
        # NOTE! This method is called by the paho-mqtt thread, thus any invocation to the
        # asyncio platform must be scheduled via `self._loop.call_soon_threadsafe()` method.
        l.debug(f"Received message from topic {msg.topic}: {str(msg.payload)}")

        # In order to correctly dispatch a message, we should look at:
        # - message destination topic
        # - message methods
        # - source device (from value in header)
        # Based on the network capture of Meross Devices, we know that there are 3 kinds of messages:
        # 1. COMMANDS sent from the app to the device (/appliance/<uuid>/subscribe) topic.
        #    Such commands have "from" header populated with "/app/<userid>-<appuuid>/subscribe" as that tells the
        #    device where to send its command ACK. Valid methods are GET/SET
        # 2. COMMAND-ACKS, which are sent back from the device to the app requesting the command execution on the
        #    "/app/<userid>-<appuuid>/subscribe" topic. Valid methods are GETACK/SETACK
        # 3. PUSH notifications, which are sent to the "/app/46884/subscribe" topic from the device (which populates
        #    the from header with its topic /appliance/<uuid>/subscribe). In this case, only the PUSH
        #    method is allowed.
        # Case 1 is not of our interest, as we don't want to get notified when the device receives the command.
        # Instead we care about case 2 to acknowledge commands from devices and case 3, triggered when another app
        # has successfully changed the state of some device on the network.

        # Let's parse the message
        message = json.loads(str(msg.payload, "utf8"))
        header = message['header']
        if not _verify_message_signature(header, self._cloud_creds.key):
            l.error(f"Invalid signature received. Message will be discarded. Message: {msg.payload}")
            return

        l.debug("Message signature OK")

        # Let's retrieve the destination topic, message method and source party:
        destination_topic = msg.topic
        message_method = header.get('method')
        source_topic = header.get('from')

        # Dispatch the message.
        # Check case 2: COMMAND_ACKS. In this case, we don't check the source topic address, as we trust it's
        # originated by a device on this network that we contacted previously.
        if destination_topic == build_client_response_topic(self._cloud_creds.user_id, self._app_id) and \
                message_method in ['PUSHACK', 'GETACK']:
            l.debug("This message is an ACK to a command this client has send.")

            # If the message is a PUSHACK/GETACK, check if there is any pending command waiting for it and, if so,
            # resolve its future
            message_id = header.get('messageId')
            future = self._pending_messages_futures.get(message_id)
            if future is not None:
                l.debug("Found a pending command waiting for response message")
                self._loop.call_soon_threadsafe(future.set_result, message)

        # Check case 3: PUSH notification.
        # Again, here we don't check the source topic, we trust that's legitimate.
        elif destination_topic == build_client_user_topic(self._cloud_creds.user_id) and message_method == 'PUSH':
            namespace = header.get('namespace')
            payload = message.get('payload')
            origin_device_uuid = device_uuid_from_push_notification(source_topic)

            parsed_push_notification = parse_push_notification(namespace=namespace,
                                                               message_payload=payload,
                                                               originating_device_uuid=origin_device_uuid)
            if parsed_push_notification is None:
                l.error("Push notification parsing failed. That message won't be dispatched.")
            else:
                self._loop.call_soon_threadsafe(self._dispatch_push_notification,
                                                parsed_push_notification)
        else:
            l.warning(f"The current implementation of this library does not handle messages received on topic "
                      f"({destination_topic}) and when the message method is {message_method}. "
                      f"If you see this message many times, it means Meross has changed the way its protocol works."
                      f"Contact the developer if that happens!")

    def _dispatch_push_notification(self, push_notification: GenericPushNotification):
        """
        This method runs within the event loop and is responsible to deliver push notifications to the
        registered event handlers.
        :param push_notification:
        :return:
        """
        # TODO
        pass

    async def _send_and_wait_ack(self, future: Future, target_device_uuid: str, message: dict):
        self._mqtt_client.publish(topic=build_device_request_topic(target_device_uuid), payload=message)

        # TODO: handle timeouts
        result = await asyncio.wait_for(future, timeout=30)
        return result

    async def async_execute_cmd(self, destination_device_uuid: str, method: str, namespace: Namespace, payload: dict):
        # Only proceed if we are connected to the remote endpoint
        if not self._mqtt_client.is_connected():
            raise UnconnectedError()

        # Build the mqtt message we will send to the broker
        message, message_id = self._build_mqtt_message(method, namespace, payload)

        # Create a future and perform the send/waiting to a task
        fut = self._loop.create_future()
        self._pending_messages_futures[message_id] = fut
        response = await loop.create_task(self._send_and_wait_ack(future=fut,
                                                                  target_device_uuid=destination_device_uuid,
                                                                  message=message))
        return response

    def _build_mqtt_message(self, method: str, namespace: Namespace, payload: dict):
        """
        Sends a message to the Meross MQTT broker, respecting the protocol payload.
        :param method:
        :param namespace:
        :param payload:
        :return:
        """

        # Generate a random 16 byte string
        randomstring = ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(16))

        # Hash it as md5
        md5_hash = md5()
        md5_hash.update(randomstring.encode('utf8'))
        messageId = md5_hash.hexdigest().lower()
        timestamp = int(round(time.time()))

        # Hash the messageId, the key and the timestamp
        md5_hash = md5()
        strtohash = "%s%s%s" % (messageId, self._cloud_creds.key, timestamp)
        md5_hash.update(strtohash.encode("utf8"))
        signature = md5_hash.hexdigest().lower()

        data = {
            "header":
                {
                    "from": self._client_response_topic,
                    "messageId": messageId,  # Example: "122e3e47835fefcd8aaf22d13ce21859"
                    "method": method,  # Example: "GET",
                    "namespace": namespace.value,  # Example: "Appliance.System.All",
                    "payloadVersion": 1,
                    "sign": signature,  # Example: "b4236ac6fb399e70c3d61e98fcb68b74",
                    "timestamp": timestamp
                },
            "payload": payload
        }
        strdata = json.dumps(data)
        return strdata.encode("utf-8"), messageId


def _generate_client_and_app_id():
    md5_hash = md5()
    rnd_uuid = UUID.uuid4()
    md5_hash.update(f"API{rnd_uuid}".encode("utf8"))
    app_id = md5_hash.hexdigest()
    client_id = 'app:%s' % md5_hash.hexdigest()
    return app_id, client_id


def _generate_mqtt_password(user_id: str, key: str):
    md5_hash = md5()
    clearpwd = f"{user_id}{key}"
    md5_hash.update(clearpwd.encode("utf8"))
    return md5_hash.hexdigest()


def _verify_message_signature(header: dict, key: str):
    message_hash = md5()
    strtohash = "%s%s%s" % (header['messageId'], key, header['timestamp'])
    message_hash.update(strtohash.encode("utf8"))
    expected_signature = message_hash.hexdigest().lower()
    return expected_signature == header['sign']


# TODO: Remove the following

async def main():
    from meross_iot.http.api import MerossHttpClient
    import os
    email = os.environ.get('MEROSS_EMAIL')
    password = os.environ.get('MEROSS_PASSWORD')

    client = await MerossHttpClient.async_from_user_password(email=email, password=password)
    devices = await client.async_list_devices()

    try:
        mqttclient = MerossMqttClient(cloud_credentials=client.cloud_credentials)
        await mqttclient.async_init()
        res = await mqttclient.async_execute_cmd('18050329735693251a0234298f1178ce', "GET", Namespace.SYSTEM_ALL, {})
        mqttclient.close()
    except:
        l.exception("Error")
    finally:
        await client.async_logout()


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    loop.close()
