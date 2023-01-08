import asyncio
import json
import logging
import ssl
from hashlib import md5
from typing import Any, List, Dict, Tuple
from paho.mqtt.client import Client, MQTTv311, MQTTMessage
from meross_iot.controller.device import BaseDevice
from meross_iot.http_api import MerossHttpClient
from meross_iot.model.enums import OnlineStatus
from meross_iot.model.http.device import HttpDeviceInfo
from meross_iot.utilities.mqtt import build_device_request_topic


_LOGGER = logging.getLogger()


class MixedQueue:
    def __init__(self, loop):
        self._queue = asyncio.Queue()
        self._loop = loop

    def sync_put_nowait(self, item):
        self._loop.call_soon(self._queue.put_nowait, item)

    def sync_put(self, item):
        asyncio.run_coroutine_threadsafe(self._queue.put(item), self._loop).result()

    def sync_get(self):
        return asyncio.run_coroutine_threadsafe(self._queue.get(), self._loop).result()

    def async_put_nowait(self, item):
        self._queue.put_nowait(item)

    async def async_put(self, item):
        await self._queue.put(item)

    async def async_get(self):
        return await self._queue.get()


class FakeDeviceSniffer:
    _mqtt_client: Client

    def __init__(self, uuid: str, mac_address: str, meross_user_id: str, meross_cloud_key: str, mqtt_host: str, mqtt_port: int):
        """Constructor"""
        self._uuid = uuid.lower()
        self._mac_address = mac_address
        self._meross_user_id = meross_user_id
        self._meross_cloud_key = meross_cloud_key
        self._mqtt_host = mqtt_host
        self._mqtt_port = mqtt_port
        self._msg_queue = MixedQueue(asyncio.get_running_loop())

        # Build the client-id
        self._client_id = f"fmware:{self._uuid}_random"

        # Start the mqtt client and connect
        self._mqtt_client = Client(client_id=self._client_id, clean_session=True, userdata=None,
                                          protocol=MQTTv311, transport="tcp", reconnect_on_failure=False)
        mac_key_digest = md5(f"{self._mac_address}{self._meross_cloud_key}".encode("utf8")).hexdigest().lower()
        device_password = f"{self._meross_user_id}_{mac_key_digest}"
        self._mqtt_client.username_pw_set(username=self._mac_address, password=device_password)

        # Set up the handlers
        self._mqtt_client.on_connect = self._on_connect
        self._mqtt_client.on_disconnect = self._on_disconnect
        self._mqtt_client.on_subscribe = self._on_subscribe
        self._mqtt_client.on_connect_fail = self._on_connection_fail
        self._mqtt_client.on_unsubscribe = self._on_subscribe
        self._mqtt_client.on_message = self._on_message

        # Prepare synchronization events
        self._started = False
        self._starting = False
        self._connected_event = asyncio.Event()
        self._subscribed_event = asyncio.Event()
        self._disconnected_event = asyncio.Event()

        # Device topic
        self._device_topic = build_device_request_topic(client_uuid=self._uuid)

    async def async_start(self, timeout: float) -> None:
        """Starts the emulation"""
        if self._started or self._starting:
            raise RuntimeError("Already Started.")

        self._starting = True
        self._mqtt_client.tls_set(ca_certs=None, certfile=None,
                                  keyfile=None, cert_reqs=ssl.CERT_REQUIRED,
                                  tls_version=ssl.PROTOCOL_TLS_CLIENT,
                                  ciphers=None)
        self._mqtt_client.connect(host=self._mqtt_host, port=self._mqtt_port)
        self._mqtt_client.loop_start()
        await asyncio.wait_for(self._connected_event.wait(), timeout)
        self._mqtt_client.subscribe(topic=self._device_topic)

    async def async_stop(self):
        if not self._started or not self._starting:
            raise RuntimeError("Not running.")
        if self._mqtt_client.is_connected():
            self._mqtt_client.disconnect()
            await self._disconnected_event.wait()
        self._mqtt_client.loop_stop()
        self._started = False

    def _on_connect(self, client: Client, userdata: Any, flags, rc):
        self._connected_event.set()

    def _on_subscribe(self, client: Client, userdata: Any, mid, granted_qos):
        self._subscribed_event.set()
        self._starting = False
        self._started = True

    def _on_connection_fail(self, client: Client, userdata):
        self._connected_event.clear()
        self._starting = False
        self._started = False

    def _on_disconnect(self, client: Client, userdata, rc):
        self._connected_event.clear()
        self._disconnected_event.set()

    def _on_unsubscribe(self, client: Client, userdata, mid):
        self._subscribed_event.clear()

    def _on_message(self, client: Client, userdata, message):
        _LOGGER.info(msg=str(message.payload))
        self._msg_queue.sync_put(message)

    async def async_wait_for_message(self, valid_methods=('SET', 'GET')) -> Tuple[MQTTMessage, str, str, Dict]:
        while True:
            raw_message: MQTTMessage = await self._msg_queue.async_get()
            parsed_message = json.loads(str(raw_message.payload, "utf8"))
            namespace = parsed_message['header']['namespace']
            method = parsed_message['header']['method']
            payload = parsed_message['payload']

            # Discard ACKs and PUSH notifications
            if method in valid_methods:
                return raw_message, namespace, method, payload
