import asyncio
import json
import logging
import random
import ssl
import string
import sys
import time
from asyncio import Future
from asyncio import TimeoutError
from hashlib import md5
from typing import Optional, List, TypeVar

import paho.mqtt.client as mqtt

from meross_iot.controller.mixins.light import LightMixin
from meross_iot.device_factory import build_meross_device
from meross_iot.http_api import MerossHttpClient
from meross_iot.model.device import BaseMerossDevice
from meross_iot.model.enums import Namespace, OnlineStatus
from meross_iot.model.exception import CommandTimeoutError
from meross_iot.model.exception import UnconnectedError
from meross_iot.model.http.device import HttpDeviceInfo
from meross_iot.model.push.factory import parse_push_notification
from meross_iot.model.push.generic import GenericPushNotification
from meross_iot.utilities.mqtt import generate_mqtt_password, generate_client_and_app_id, build_client_response_topic, \
    build_client_user_topic, verify_message_signature, device_uuid_from_push_notification, build_device_request_topic

logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.INFO, stream=sys.stdout)
_LOGGER = logging.getLogger(__name__)


T = TypeVar('T', bound=BaseMerossDevice)      # Declare type variable


class MerossManager(object):
    """
    This class handles MQTT exchange with Meross MQTT broker.
    """

    def __init__(self,
                 http_client: Optional[MerossHttpClient] = None,
                 auto_reconnect: Optional[bool] = True,
                 domain: Optional[str] = "iot.meross.com",
                 port: Optional[int] = 2001,
                 ca_cert: Optional[str] = None,
                 *args,
                 **kwords) -> None:

        # Store local attributes
        self._http_client = http_client
        self._cloud_creds = self._http_client.cloud_credentials
        self._auto_reconnect = auto_reconnect
        self._domain = domain
        self._port = port
        self._ca_cert = ca_cert
        self._app_id, self._client_id = generate_client_and_app_id()
        self._pending_messages_futures = {}
        self._device_registry = DeviceRegistry()

        # Setup mqtt client
        mqtt_pass = generate_mqtt_password(user_id=self._cloud_creds.user_id, key=self._cloud_creds.key)
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
        _LOGGER.info("Disconnecting from mqtt")
        self._mqtt_client.disconnect()
        _LOGGER.debug("Stopping the MQTT looper.")
        self._mqtt_client.loop_stop(True)
        _LOGGER.info("MQTT Client has fully disconnected.")

    def find_device(self, uuids: Optional[List[str]] = None,
                    device_type: Optional[str] = None,
                    device_class: Optional[type] = None,
                    device_name: Optional[str] = None,
                    online_status: Optional[OnlineStatus] = None) -> List[T]:
        return self._device_registry.find_all_by(
            uuids=uuids, device_type=device_type, device_class=device_class,
            device_name=device_name, online_status=online_status)

    async def async_init(self) -> None:
        """
        Connects to the remote MQTT broker and subscribes to the relevant topics.
        :return:
        """

        _LOGGER.info("Initializing the MQTT connection...")
        self._mqtt_client.connect(host=self._domain, port=self._port, keepalive=30)

        # Starts a new thread that handles mqtt protocol and calls us back via callbacks
        _LOGGER.debug("Starting the MQTT looper.")
        self._mqtt_client.loop_start()

        # Wait until the client connects and subscribes to the broken
        await self._mqtt_connected_and_subscribed.wait()
        self._mqtt_connected_and_subscribed.clear()
        _LOGGER.debug("Connected and subscribed to relevant topics")

    async def async_device_discovery(self):
        """
        Fetch devices and online status from HTTP API. This method also notifies/updates local device online/offline
        status.
        :return:
        """
        # List http devices
        http_devices = await self._http_client.async_list_devices()

        # Update state of local devices
        discovered_new_http_devices = []
        for hdevice in http_devices:
            ldevice = self._device_registry.lookup_by_uuid(hdevice.uuid)
            if ldevice is not None:
                _LOGGER.info(f"Updating state of device {ldevice.name} ({ldevice.uuid}) from HTTP info...")
                ldevice.update_from_http_state(hdevice)
            else:
                # If the http_device was not locally registered, keep track of it as we will add it later.
                _LOGGER.info(f"Discovery found a new Meross device {hdevice.dev_name} ({hdevice.uuid}).")
                discovered_new_http_devices.append(hdevice)

        # Check if we got devices that were not listed from http.
        # This should not happen as the UNBIND event should take care of it.
        # So we just raise a warning if that happens.
        inconsistent_local_devices = []
        for ldevice in self._device_registry.find_all_by():
            found_in_http = False
            for hdevice in http_devices:
                if hdevice.uuid == ldevice.uuid:
                    found_in_http = True
                    break
            if not found_in_http:
                inconsistent_local_devices.append(ldevice)
                _LOGGER.warning(f"Device {ldevice.name} ({ldevice.uuid}) is locally registered but has not been "
                                f"reported by the last HTTP API device-list call.")

        # If the http-device is an hub, then list its subdevices
        # TODO: list sub-devices

        # TODO: handle inconsistent devices?
        # For every newly discovered device, retrieve its abilities and then build a corresponding wrapper.
        # Do this in "parallel" with multiple tasks rather than executing every task singularly
        tasks = []
        for d in discovered_new_http_devices:
            tasks.append(self._loop.create_task(self._async_enroll_new_http_dev(d)))

        # Wait for factory to build all devices
        enrolled_devices = await asyncio.gather(*tasks, loop=self._loop)

        # TODO add result logging
        _LOGGER.debug("HTTP async completed.")

    async def _async_enroll_new_http_dev(self, device_info: HttpDeviceInfo) -> Optional[BaseMerossDevice]:
        try:
            res_abilities = await self.async_execute_cmd(destination_device_uuid=device_info.uuid,
                                                         method="GET",
                                                         namespace=Namespace.SYSTEM_ABILITY,
                                                         payload={})
            abilities = res_abilities.get('ability')
        except CommandTimeoutError:
            _LOGGER.error(f"Failed to retrieve abilities for device {device_info.dev_name} ({device_info.uuid}). "
                          f"This device won't be enrolled.")
            return None

        # Build a full-featured device using the given ability set
        device = build_meross_device(http_device_info=device_info, device_abilities=abilities, manager=self)

        # Enroll the device
        self._device_registry.enroll_device(device)
        return device

    def _on_connect(self, client, userdata, rc, other):
        # NOTE! This method is called by the paho-mqtt thread, thus any invocation to the
        # asyncio platform must be scheduled via `self._loop.call_soon_threadsafe()` method.

        _LOGGER.debug(f"Connected with result code {rc}")
        # Subscribe to the relevant topics
        _LOGGER.debug("Subscribing to topics...")
        client.subscribe([(self._user_topic, 0), (self._client_response_topic, 0)])

    def _on_disconnect(self, client, userdata, rc):
        # NOTE! This method is called by the paho-mqtt thread, thus any invocation to the
        # asyncio platform must be scheduled via `self._loop.call_soon_threadsafe()` method.

        _LOGGER.info("Disconnection detected. Reason: %s" % str(rc))

        # If the client disconnected explicitly, the mqtt library handles thred stop autonomously
        if rc == mqtt.MQTT_ERR_SUCCESS:
            pass
        else:
            # Otherwise, if the disconnection was not intentional, we probably had a connection drop.
            # In this case, we only stop the loop thread if auto_reconnect is not set. In fact, the loop will
            # handle reconnection autonomously on connection drops.
            if not self._auto_reconnect:
                _LOGGER.info("Stopping mqtt loop on connection drop")
                client.loop_stop(True)
            else:
                _LOGGER.warning("Client has been disconnected, however auto_reconnect flag is set. "
                          "Won't stop the looping thread, as it will retry to connect.")

    def _on_unsubscribe(self):
        # NOTE! This method is called by the paho-mqtt thread, thus any invocation to the
        # asyncio platform must be scheduled via `self._loop.call_soon_threadsafe()` method.
        _LOGGER.debug("Unsubscribed from topics")

    def _on_subscribe(self, client, userdata, mid, granted_qos):
        # NOTE! This method is called by the paho-mqtt thread, thus any invocation to the
        # asyncio platform must be scheduled via `self._loop.call_soon_threadsafe()` method.
        _LOGGER.debug("Succesfully subscribed to topics.")
        self._loop.call_soon_threadsafe(
            self._mqtt_connected_and_subscribed.set
        )

    def _on_message(self, client, userdata, msg):
        # NOTE! This method is called by the paho-mqtt thread, thus any invocation to the
        # asyncio platform must be scheduled via `self._loop.call_soon_threadsafe()` method.
        _LOGGER.debug(f"Received message from topic {msg.topic}: {str(msg.payload)}")

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
        if not verify_message_signature(header, self._cloud_creds.key):
            _LOGGER.error(f"Invalid signature received. Message will be discarded. Message: {msg.payload}")
            return

        _LOGGER.debug("Message signature OK")

        # Let's retrieve the destination topic, message method and source party:
        destination_topic = msg.topic
        message_method = header.get('method')
        source_topic = header.get('from')

        # Dispatch the message.
        # Check case 2: COMMAND_ACKS. In this case, we don't check the source topic address, as we trust it's
        # originated by a device on this network that we contacted previously.
        if destination_topic == build_client_response_topic(self._cloud_creds.user_id, self._app_id) and \
                message_method in ['SETACK', 'GETACK']:
            _LOGGER.debug("This message is an ACK to a command this client has send.")

            # If the message is a PUSHACK/GETACK, check if there is any pending command waiting for it and, if so,
            # resolve its future
            message_id = header.get('messageId')
            future = self._pending_messages_futures.get(message_id)
            if future is not None:
                _LOGGER.debug("Found a pending command waiting for response message")
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
                _LOGGER.error("Push notification parsing failed. That message won't be dispatched.")
            else:
                asyncio.run_coroutine_threadsafe(self._dispatch_push_notification(parsed_push_notification), self._loop)
        else:
            _LOGGER.warning(f"The current implementation of this library does not handle messages received on topic "
                            f"({destination_topic}) and when the message method is {message_method}. "
                            "If you see this message many times, it means Meross has changed the way its protocol "
                            "works. Contact the developer if that happens!")

    async def _dispatch_push_notification(self, push_notification: GenericPushNotification) -> bool:
        """
        This method runs within the event loop and is responsible to deliver push notifications to the corresponding
        meross device within the register.
        :param push_notification:
        :return:
        """
        # TODO: handle generic push notification as Bind/Unbind

        # Lookup the originating device and deliver the push notification to that one.
        target_devs = self._device_registry.find_all_by(push_notification.originating_device_uuid)
        if len(target_devs) < 1:
            _LOGGER.warning("Received a push notification for a device that is not available in the local registry. "
                            "You may need to trigger a discovery to catch those updates. Device-UUID: "
                            f"{push_notification.originating_device_uuid}")
            # TODO: does it make sense to schedule a device discover at this stage without needing to warn the user?
            return False

        # Pass the control to the specific device implementation
        dev = target_devs[0]
        handled = dev.handle_push_notification(push_notification)
        if not handled:
            _LOGGER.warning(f"Uncaught push notification {push_notification.namespace}")

        return handled

    async def async_execute_cmd(self,
                                destination_device_uuid: str,
                                method: str,
                                namespace: Namespace,
                                payload: dict,
                                timeout: float = 5.0):
        """
        Executes a command
        :param destination_device_uuid:
        :param method:
        :param namespace:
        :param payload:
        :param timeout:
        :return:
        """
        # Only proceed if we are connected to the remote endpoint
        if not self._mqtt_client.is_connected():
            _LOGGER.error("The MQTT client is not connected to the remote broker. Have you called async_init()?")
            raise UnconnectedError()

        # Build the mqtt message we will send to the broker
        message, message_id = self._build_mqtt_message(method, namespace, payload)

        # Create a future and perform the send/waiting to a task
        fut = self._loop.create_future()
        self._pending_messages_futures[message_id] = fut

        response = await self._async_send_and_wait_ack(future=fut,
                                                       target_device_uuid=destination_device_uuid,
                                                       message=message,
                                                       timeout=timeout)
        return response.get('payload')

    async def _async_send_and_wait_ack(self, future: Future, target_device_uuid: str, message: dict, timeout: float):
        md = self._mqtt_client.publish(topic=build_device_request_topic(target_device_uuid), payload=message)
        try:
            return await asyncio.wait_for(future, timeout, loop=self._loop)
        except TimeoutError as e:
            _LOGGER.error(f"Timeout occurred while waiting a response for message {message} sent to device uuid "
                          f"{target_device_uuid}. Timeout was: {timeout} seconds")
            raise CommandTimeoutError()

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


class DeviceRegistry(object):
    def __init__(self):
        self._devices_by_uuid = {}

    def relinquish_device(self, device_uuid: str):
        dev = self._devices_by_uuid.get(device_uuid)
        if dev is None:
            raise ValueError(f"Cannot relinquish device {device_uuid} as it does not belong to this registry.")

        # Dismiss the device
        # TODO: implement the dismiss() method to release device-held resources
        _LOGGER.debug(f"Disposing resources for {dev.name} ({dev.uuid})")
        dev.dismiss()
        del self._devices_by_uuid[dev]
        _LOGGER.info(f"Device {dev.name} ({dev.uuid}) removed from registry")

    def enroll_device(self, device: BaseMerossDevice):
        if device.uuid in self._devices_by_uuid:
            _LOGGER.warning(f"Device {device.name} ({device.uuid}) has been already added to the registry.")
            return
        else:
            _LOGGER.debug(f"Adding device {device.name} ({device.uuid}) to registry.")
            self._devices_by_uuid[device.uuid] = device

    def lookup_by_uuid(self,
                       uuid: str) -> Optional[BaseMerossDevice]:
        return self._devices_by_uuid.get(uuid)

    def find_all_by(self,
                    uuids: Optional[List[str]] = None,
                    device_type: Optional[str] = None,
                    device_class: Optional[T] = None,
                    device_name: Optional[str] = None,
                    online_status: Optional[OnlineStatus] = None) -> List[BaseMerossDevice]:

        # Look by UUIDs
        if uuids is not None:
            res = filter(lambda d: d.uuid in uuids, self._devices_by_uuid.values())
        else:
            res = self._devices_by_uuid.values()

        if device_type is not None:
            res = filter(lambda d: d.type == device_type, res)
        if online_status is not None:
            res = filter(lambda d: d.online_status == online_status, res)
        if device_class is not None:
            res = filter(lambda d: isinstance(d, device_class), res)
        if device_name is not None:
            res = filter(lambda d: d.name == device_name, res)

        return list(res)
