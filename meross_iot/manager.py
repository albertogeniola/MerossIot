import asyncio
import json
import logging
import random
import ssl
import string
import sys
from asyncio import Future, AbstractEventLoop
from asyncio import TimeoutError
from datetime import datetime
from enum import Enum
from hashlib import md5
from time import time
from typing import Optional, List, TypeVar, Iterable, Callable, Awaitable, Tuple, Union, Any

import paho.mqtt.client as mqtt
from aiohttp import ClientSession

from meross_iot.controller.device import BaseDevice, HubDevice, GenericSubDevice
from meross_iot.device_factory import (
    build_meross_device_from_abilities,
    build_meross_subdevice,
    build_meross_device_from_known_types,
)
from meross_iot.error_budget import ErrorBudgetManager
from meross_iot.http_api import MerossHttpClient
from meross_iot.model.constants import DEFAULT_COMMAND_TIMEOUT, DEFAULT_MQTT_PORT
from meross_iot.model.enums import Namespace, OnlineStatus
from meross_iot.model.exception import (
    CommandTimeoutError,
    CommandError,
    UnknownDeviceType
)
from meross_iot.model.http.device import HttpDeviceInfo
from meross_iot.model.http.subdevice import HttpSubdeviceInfo
from meross_iot.model.push.factory import parse_push_notification
from meross_iot.model.push.generic import GenericPushNotification
from meross_iot.model.push.online import OnlinePushNotification
from meross_iot.model.push.unbind import UnbindPushNotification
from meross_iot.utilities.mqtt import (
    generate_mqtt_password,
    generate_client_and_app_id,
    build_client_response_topic,
    build_client_user_topic,
    verify_message_signature,
    device_uuid_from_push_notification,
    build_device_request_topic,
)
from meross_iot.utilities.network import extract_domain

logging.basicConfig(
    format="%(levelname)s:%(message)s", level=logging.INFO, stream=sys.stdout
)
_LOGGER = logging.getLogger(__name__)

_CONNECTION_DROP_UPDATE_SCHEDULE_INTERVAL = 2

T = TypeVar("T", bound=BaseDevice)  # Declare type variable
ManagerPushNotificationHandlerType = Callable[[GenericPushNotification, List[BaseDevice], 'MerossManager'], Awaitable]

_PENDING_FUTURES = []


def _mqtt_key_from_domain_port(domain: str, port: int) -> str:
    return f"{domain}:{port}"


class TransportMode(Enum):
    MQTT_ONLY = 0
    LAN_HTTP_FIRST = 1
    LAN_HTTP_FIRST_ONLY_GET = 2


class MqttConnectionStatus(Enum):
    DISCONNECTED = "DISCONNECTED"
    CONNECTING = "CONNECTING"
    CONNECTED = "CONNECTED"


class MerossManager(object):
    """
    This class implements a full-features Meross Client, which provides device discovery and registry.
    *Note*: The manager must be initialized before invoking any of its discovery/registry methods.
    """

    def __init__(
            self,
            http_client: MerossHttpClient,
            auto_reconnect: Optional[bool] = True,
            mqtt_skip_cert_validation: bool = False,
            ca_cert: Optional[str] = None,
            loop: Optional[AbstractEventLoop] = None,
            mqtt_override_server: Optional[Tuple[str, int]] = None,
            auto_discovery_on_connection: bool = True,
            *args,
            **kwords,
    ) -> None:
        """
        Constructor
        :param http_client: MerossHttpClient object that is used by the manager to query the HTTP API
                            (for device discovery, etc)
        :param auto_reconnect: (Optional) When True, the mqtt client will automatically reconnect when the connection
                               drops. Defaults to True.
        :param mqtt_skip_cert_validation: (Optional) When set the Manager will accept unverified SSL/TLS certificates
                                          from the remote MQTT server. Defaults to False.
        :param ca_cert: (Optional) Path to the PEM certificate to trust (Intermediate/CA)
        :param loop: (Optional) Asyncio loop to use
        :param args:
        :param mqtt_override_server: (Optional) Tuple (hostname, port) of the MQTT server to use for MQTT connection.
                                     When None (default), the hostname will be extracted by the domain/reserved domain
                                     obtained via HTTP API, and port 443 will be used.
        :param auto_discovery_on_connection: (Optional) When set instructs the manager to issue a discovery as soon as
                                             the mqtt connection is established against the MQTT broker (defaults to True)
        """

        # Store local attributes
        self._http_client = http_client
        self._cloud_creds = self._http_client.cloud_credentials
        self._auto_reconnect = auto_reconnect
        self._ca_cert = ca_cert
        self._app_id, self._client_id = generate_client_and_app_id()
        self._pending_messages_futures = {}
        self._device_registry = DeviceRegistry()
        self._push_coros = []
        self._mqtt_skip_validation = mqtt_skip_cert_validation
        self._mqtt_clients = {}
        self._mqtt_connected_and_subscribed = {}
        self._auto_discovery_on_connection = auto_discovery_on_connection

        # By default, assume MQTT-Only transport mode
        self._default_transport_mode = TransportMode.MQTT_ONLY
        self._error_budget_manager = ErrorBudgetManager()

        # Default proxy setup
        self._enable_proxy = False
        self._proxy_type = None
        self._proxy_addr = None
        self._proxy_port = None

        # Setup synchronization primitives
        self._mqtt_looper_task = None
        self._loop = asyncio.get_event_loop() if loop is None else loop

        # Prepare MQTT info
        self._mqtt_password = generate_mqtt_password(user_id=self._cloud_creds.user_id, key=self._cloud_creds.key)
        self._client_response_topic = build_client_response_topic(
            user_id=self._cloud_creds.user_id, app_id=self._app_id
        )
        self._user_topic = build_client_user_topic(user_id=self._cloud_creds.user_id)
        self._override_mqtt_server = mqtt_override_server

    @property
    def auto_discovery_on_connection(self) -> bool:
        """When set, tells the manager to automatically issue a discovery after a successful connection"""
        return self._auto_discovery_on_connection

    @auto_discovery_on_connection.setter
    def auto_discovery_on_connection(self, val: bool):
        self._auto_discovery_on_connection = val

    @property
    def default_transport_mode(self) -> TransportMode:
        return self._default_transport_mode

    @default_transport_mode.setter
    def default_transport_mode(self, value: TransportMode) -> None:
        self._default_transport_mode = value

    def _get_client_from_domain_port(self, client: mqtt.Client) -> Tuple[Optional[str], Optional[int]]:
        for k, v in self._mqtt_clients.items():
            if v == client:
                domain, port = k.split(":")
                return domain, int(port)
        return None, None

    async def _async_get_create_mqtt_client(self, domain: str, port: int) -> mqtt.Client:
        """
        Retrieves the mqtt_client for the given domain/port combination.
        If not existing, a new one is created
        """
        dict_key = _mqtt_key_from_domain_port(domain=domain, port=port)
        client = self._mqtt_clients.get(dict_key)
        if client is not None:
            _LOGGER.debug("MQTT Client for %s already available.", dict_key)
        else:
            _LOGGER.info("Allocating new mqtt client for %s...", dict_key)
            client = self._new_mqtt_client()
            client.user_data_set(dict_key)
            if self._enable_proxy:
                _LOGGER.info("Proxy configuration set for newly created client")
                client.proxy_set(proxy_type=self._proxy_type, proxy_addr=self._proxy_addr, proxy_port=self._proxy_port)
            self._mqtt_clients[dict_key] = client
        # Init the client
        if not client.is_connected():
            conn_evt = self._mqtt_connected_and_subscribed.get(dict_key)  # type: asyncio.Event
            if conn_evt is None:
                conn_evt = asyncio.Event()
                _LOGGER.debug("MQTT client connecting to %s:%d", domain, port)
                client.connect(host=domain, port=port, keepalive=30)
                self._mqtt_connected_and_subscribed[dict_key] = conn_evt
            # Start the client looper
            client.loop_start()
            # Wait for the client to connect
            await conn_evt.wait()
        return client

    def _new_mqtt_client(self) -> mqtt.Client:
        # Setup mqtt client
        client = mqtt.Client(client_id=self._client_id, protocol=mqtt.MQTTv311, clean_session=False)
        client.username_pw_set(username=self._cloud_creds.user_id, password=self._mqtt_password)

        # Certificate validation setup
        client.tls_set(
            ca_certs=self._ca_cert,
            certfile=None,
            keyfile=None,
            cert_reqs=ssl.CERT_NONE if self._mqtt_skip_validation else ssl.CERT_REQUIRED,
            tls_version=ssl.PROTOCOL_TLS_CLIENT,
            ciphers=None,
        )
        client.tls_insecure_set(self._mqtt_skip_validation)

        # Setup Callbacks
        client.on_connect = self._on_connect
        client.on_message = self._on_message
        client.on_disconnect = self._on_disconnect
        client.on_subscribe = self._on_subscribe

        return client

    def register_push_notification_handler_coroutine(
            self, coro: ManagerPushNotificationHandlerType
    ) -> None:
        """
        Registers a coroutine so that it gets invoked whenever a push notification is received from the Meross
        MQTT broker.
        :param coro: coroutine-function: a function that, when invoked, returns a Coroutine object that can be awaited.
        :return:
        """
        if not asyncio.iscoroutinefunction(coro):
            raise ValueError("The coro parameter must be a coroutine function")
        if coro in self._push_coros:
            _LOGGER.error(
                f"Coroutine {coro} was already added to event handlers of this device"
            )
            return
        self._push_coros.append(coro)

    def unregister_push_notification_handler_coroutine(
            self, coro: ManagerPushNotificationHandlerType
    ) -> None:
        """
        Unregisters the event handler
        :param coro: coroutine-function: a function that, when invoked, returns a Coroutine object that can be awaited.
                     This coroutine function should have been previously registered
        :return:
        """
        if coro in self._push_coros:
            self._push_coros.remove(coro)
        else:
            _LOGGER.error(
                f"Coroutine function {coro} was not registered as handler for this device"
            )

    def close(self):
        _LOGGER.info("Manager stop requested.")
        _LOGGER.debug("Canceling pending futures...")
        for f in _PENDING_FUTURES:
            if not f.cancelled():
                f.cancel()
        # Disconnect from all mqtt clients
        for client in self._mqtt_clients.values():
            client.disconnect()

    def find_devices(
            self,
            device_uuids: Optional[Iterable[str]] = None,
            internal_ids: Optional[Iterable[str]] = None,
            device_type: Optional[str] = None,
            device_class: Optional[Union[type, Iterable[type]]] = None,
            device_name: Optional[str] = None,
            online_status: Optional[OnlineStatus] = None,
    ) -> List[T]:
        """
        Lists devices that have been discovered via this manager. When invoked with no arguments,
        it returns the whole list of registered devices. When one or more filter arguments are specified,
        it returns the list of devices that satisfy all the filters (consider multiple filters as in logical AND).

        :param device_uuids: List of Meross native device UUIDs. When specified, only devices that have a native UUID
            contained in this list are returned.
        :param internal_ids: Iterable List of MerossIot device ids. When specified, only devices that have a
            derived-ids contained in this list are returned.
        :param device_type: Device type string as reported by meross app (e.g. "mss310" or "msl120"). Note that this
            field is case sensitive.
        :param device_class: Filter based on the resulting device class or list of classes. When this parameter is
            a list of types, the filter returns al the devices that matches at least one of the types in the list
            (logic OR). You can filter also for capability Mixins, such as
            :code:`meross_iot.controller.mixins.toggle.ToggleXMixin` (returns all the devices supporting ToggleX
            capability) or :code:`meross_iot.controller.mixins.light.LightMixin`
            (returns all the device that supports light control). Similarly, you can identify all the HUB devices
            by specifying :code:`meross_iot.controller.device.HubDevice`, Sensors as
            :code:`meross_iot.controller.subdevice.Ms100Sensor` and Valves as
            :code:`meross_iot.controller.subdevice.Mts100v3Valve`.
        :param device_name: Filter the devices based on their assigned name (case sensitive)
        :param online_status: Filter the devices based on their :code:`meross_iot.model.enums.OnlineStatus`
            as reported by the HTTP api or byt the relative hub (when dealing with subdevices).
        :return:
            The list of devices that match the provided filters, if any.
        """
        return self._device_registry.find_all_by(
            device_uuids=device_uuids,
            internal_ids=internal_ids,
            device_type=device_type,
            device_class=device_class,
            device_name=device_name,
            online_status=online_status,
        )

    async def async_device_discovery(
            self,
            update_subdevice_status: bool = True,
            meross_device_uuid: str = None,
            cached_http_device_list: Optional[Iterable[HttpDeviceInfo]] = None
    ) -> Iterable[BaseDevice]:
        """
        Fetch devices and online status from HTTP API. This method also notifies/updates local device online/offline
        status.

        :param meross_device_uuid: Meross UUID of the device that the user wants to discover (is already known).
            This parameter restricts the discovery only to that particular device.

        :param update_subdevice_status: When True, tells the manager to retrieve the HUB status in order to update
            hub-subdevice online status, which would be UNKNOWN if not explicitly retrieved.

        :param cached_http_device_list: List/Iterable structure of HttpDeviceInfo to be used for the discovery.
            When passed, the manger skips the HTTP API call and uses this data to perform MQTT discovery.
            When not passed, the manager will issue the HTTP API call to retrieve the latest HTTP devices list

        :return: A list of discovered device, which implement `BaseDevice`
        """
        if cached_http_device_list is None:
            _LOGGER.info(f"\n\n------- Triggering Manager Discovery, filter_device: [{meross_device_uuid}] -------")
            http_devices = await self._http_client.async_list_devices()
        else:
            _LOGGER.info(
                f"\n\n------- Triggering Manager Discovery (using cached http device list), filter_device: [{meross_device_uuid}] -------")
            http_devices = cached_http_device_list

        # If the user pased a specific uuid, filter the list by that one
        if meross_device_uuid is not None:
            http_devices = filter(lambda d: d.uuid == meross_device_uuid, http_devices)

        # Update state of local devices
        discovered_new_http_devices = []
        already_known_http_devices = {}
        for hdevice in http_devices:
            # Check if the device is already present into the registry
            ldevice = self._device_registry.lookup_base_by_uuid(hdevice.uuid)
            if ldevice is not None:
                already_known_http_devices[hdevice] = ldevice
            else:
                # If the http_device was not locally registered, keep track of it as we will add it later.
                discovered_new_http_devices.append(hdevice)

        # Give some info
        _LOGGER.debug(
            f"The following devices were already known to me: {already_known_http_devices}"
        )
        _LOGGER.debug(
            f"The following devices are new to me: {discovered_new_http_devices}"
        )

        enrolled_devices = []
        for d in discovered_new_http_devices:
            dev = await self._async_enroll_new_http_dev(d)
            enrolled_devices.append(dev)
        for hdevice, ldevice in already_known_http_devices.items():
            dev = await ldevice.update_from_http_state(hdevice)
            enrolled_devices.append(dev)

        _LOGGER.debug(
            f"Updating %d known devices form HTTPINFO and fetching "
            f"data from %d newly discovered devices...",
            len(already_known_http_devices),
            len(discovered_new_http_devices)
        )

        _LOGGER.info(f"Fetch and update done")

        hubs = []
        enrolled_subdevices = []
        for d in enrolled_devices:
            if isinstance(d, HubDevice):
                hubs.append(d)
                subdevs = await self._http_client.async_list_hub_subdevices(
                    hub_id=d.uuid
                )
                for sd in subdevs:
                    dev = await self._async_enroll_new_http_subdev(
                        subdevice_info=sd,
                        hub=d,
                        hub_reported_abilities=d.abilities)
                    enrolled_subdevices.append(dev)

        # We need to update the state of hubs in order to refresh subdevices online status
        if update_subdevice_status:
            for h in hubs:
                await h.async_update(drop_on_overquota=False)
        _LOGGER.info(f"\n------- Manager Discovery ended -------\n")

        res = []
        res.extend(enrolled_devices)
        res.extend(enrolled_subdevices)
        return res

    async def _async_enroll_new_http_subdev(
            self,
            subdevice_info: HttpSubdeviceInfo,
            hub: HubDevice,
            hub_reported_abilities: dict,
    ) -> Optional[GenericSubDevice]:
        subdevice = build_meross_subdevice(
            http_subdevice_info=subdevice_info,
            hub_uuid=hub.uuid,
            hub_reported_abilities=hub_reported_abilities,
            manager=self,
        )
        # Register the device to the hub
        if hub.get_subdevice(subdevice_id=subdevice.subdevice_id) is None:
            hub.register_subdevice(subdevice=subdevice)
        else:
            _LOGGER.debug("HUB %s already knows subdevice %s", hub.uuid, subdevice)

        # Enroll the device
        self._device_registry.enroll_device(subdevice)
        return subdevice

    async def async_init(self):
        """
        @deprecated
        Ignored, signature left for backward compatibility
        """
        pass

    async def _async_enroll_new_http_dev(
            self, device_info: HttpDeviceInfo
    ) -> Optional[BaseDevice]:
        # If the device is online, try to query the device for its abilities.
        device = None
        abilities = None
        if device_info.online_status == OnlineStatus.ONLINE:
            try:
                res_abilities = await self.async_execute_cmd(
                    destination_device_uuid=device_info.uuid,
                    method="GET",
                    namespace=Namespace.SYSTEM_ABILITY,
                    payload={},
                    mqtt_hostname=extract_domain(device_info.domain),
                    mqtt_port=DEFAULT_MQTT_PORT
                )
                abilities = res_abilities.get("ability")
            except CommandTimeoutError:
                _LOGGER.warning(
                    f"Device %s (%s) is online, but timeout occurred "
                    f"when fetching its abilities. ", str(device_info.dev_name), str(device_info.uuid)
                )
        if abilities is not None:
            # Build a full-featured device using the given ability set
            device = build_meross_device_from_abilities(
                http_device_info=device_info, device_abilities=abilities, manager=self
            )
        else:
            # In case we failed to build device's abilities at runtime, try to build the device statically
            # based on its model type.
            try:
                device = build_meross_device_from_known_types(
                    http_device_info=device_info, manager=self
                )
                _LOGGER.info(
                    "Device %s (%s) was built statically via known "
                    "types, because we failed to retrieve updated abilities for the given device.",
                    device_info.dev_name, str(device_info.uuid)
                )
            except UnknownDeviceType:
                _LOGGER.debug("Could not build statically device %s (%s) as it's not a known type.",
                              device_info.dev_name, device_info.uuid)

        # Enroll the device
        if device is not None:
            self._device_registry.enroll_device(device)
            return device

    def _on_connect(self, client: mqtt.Client, userdata, rc, other):
        # NOTE! This method is called by the paho-mqtt thread, thus any invocation to the
        # asyncio platform must be scheduled via `self._loop.call_soon_threadsafe()` method.
        topics = [(self._user_topic, 1), (self._client_response_topic, 1)]

        _LOGGER.debug(f"Connected with result code {rc}")
        # Subscribe to the relevant topics
        _LOGGER.debug("Subscribing to topics...")
        result, mid = client.subscribe(topics)

        if result != mqtt.MQTT_ERR_SUCCESS:
            _LOGGER.error("Failed to subscribe to topics %s", str(topics))

    def _on_disconnect(self, client: mqtt.Client, userdata, rc):
        # NOTE! This method is called by the paho-mqtt thread, thus any invocation to the
        # asyncio platform must be scheduled via `self._loop.call_soon_threadsafe()` method.
        _LOGGER.info("Disconnection detected. Reason: %s" % str(rc))

        # When a disconnection occurs, we need to set "unavailable" status.
        asyncio.run_coroutine_threadsafe(
            self._notify_connection_drop(), loop=self._loop
        )

        conn_evt = self._mqtt_connected_and_subscribed.get(userdata) # type: asyncio.Event
        conn_evt.clear()

    def _on_unsubscribe(self):
        # NOTE! This method is called by the paho-mqtt thread, thus any invocation to the
        # asyncio platform must be scheduled via `self._loop.call_soon_threadsafe()` method.
        _LOGGER.debug("Unsubscribed from topics")

    def _on_subscribe(self, client: mqtt.Client, userdata, mid, granted_qos):
        # NOTE! This method is called by the paho-mqtt thread, thus any invocation to the
        # asyncio platform must be scheduled via `self._loop.call_soon_threadsafe()` method.
        _LOGGER.debug("Successfully subscribed to topics.")
        sub_event = self._mqtt_connected_and_subscribed.get(userdata)
        self._loop.call_soon_threadsafe(sub_event.set)

        # When the connection happens after a disconnection (i.e. it is a re-connection)
        # we need to trigger Online Events for devices which where offline before.
        # Also, we want to update entirely the device status
        # To avoid flooding, schedule updates every 2s intervals.
        _LOGGER.info(
            "Subscribed to topics, scheduling state update for already known devices."
        )

        async def _update_devices_after_reconnection():
            # In case of reconnections, we need to issue a device_discovery via HTTP in order to update
            # ONLINE state. We also need to manually trigger "ONLINE" events for devices that resulted to be
            # OFFLINE and went ONLINE while our manager was off-network. To do so, we store into a dict the previous
            # online state and then issue the update only for devices that changed their state

            # Store the previous connection state for all known devices
            _prev_online_status = {d.uuid: d.online_status for d in self.find_devices()}

            # Issue a new discovery to update their connection status. This will rely on HTTP api to update it
            await self.async_device_discovery(update_subdevice_status=True)

            i = 0
            for d in self.find_devices():
                old_status = _prev_online_status.get(d.uuid)
                if old_status is None:
                    # This is a new device that has been added while we were offline.
                    _LOGGER.warning("Found a new device %s that has become online while we were offline.", d)
                    # TODO: do we need to issue a BINDING event manually here?
                    continue
                else:
                    _schedule_later(self._update_and_send_push(dev=d, old_status=old_status), start_delay=i,
                                    loop=self._loop)
                    i += 1

        # If a connection drop occurs, we must update the device state in order to be consistent
        # TODO: Do we need to issue this command only when connection drops occur or also at first connection attempt?
        if self._auto_discovery_on_connection:
            asyncio.run_coroutine_threadsafe(coro=_update_devices_after_reconnection(), loop=self._loop)

    async def _update_and_send_push(self, dev: BaseDevice, old_status: OnlineStatus) -> None:
        if dev.online_status == OnlineStatus.ONLINE:
            # In case the device was known and is ONLINE, we want to manually update its status
            _LOGGER.warning("Updating status for device %s", dev)
            await dev.async_update()

        # In case the device was known and is not ONLINE, we just send the ONLINE push notification
        if dev.online_status != old_status:
            _LOGGER.warning("Device %s changed its online status while manager was offline (was %s, now is %s). "
                            "Sending event manually.", dev, old_status, dev.online_status)
            await dev.async_handle_push_notification(namespace=Namespace.SYSTEM_ONLINE,
                                                     data={'online': {'status': dev.online_status.value}})

    def _on_message(self, client, userdata, msg):
        # NOTE! This method is called by the paho-mqtt thread, thus any invocation to the
        # asyncio platform must be scheduled via `self._loop.call_soon_threadsafe()` method.
        _LOGGER.debug(f"Received message from topic {msg.topic}: {str(msg.payload)}")

        # In order to correctly dispatch a message, we should look at:
        # - message destination topic
        # - message methods
        # - source device (from value in header)
        # Based on the network capture of Meross Devices, we know that there are 4 kinds of messages:
        # 1. COMMANDS sent from the app to the device (/appliance/<uuid>/subscribe) topic.
        #    Such commands have "from" header populated with "/app/<userid>-<appuuid>/subscribe" as that tells the
        #    device where to send its command ACK. Valid methods are GET/SET
        # 2. COMMAND-ACKS, which are sent back from the device to the app requesting the command execution on the
        #    "/app/<userid>-<appuuid>/subscribe" topic. Valid methods are GETACK/SETACK/ERROR
        # 3. PUSH notifications, which are sent to the "/app/46884/subscribe" topic from the device (which populates
        #    the from header with its topic /appliance/<uuid>/subscribe). In this case, only the PUSH
        #    method is allowed.
        # Case 1 is not of our interest, as we don't want to get notified when the device receives the command.
        # Instead we care about case 2 to acknowledge commands from devices and case 3, triggered when another app
        # has successfully changed the state of some device on the network.

        # Let's parse the message
        message = json.loads(str(msg.payload, "utf8"))
        header = message["header"]
        if not verify_message_signature(header, self._cloud_creds.key):
            _LOGGER.error(
                f"Invalid signature received. Message will be discarded. Message: {msg.payload}"
            )
            return

        _LOGGER.debug("Message signature OK")

        # Let's retrieve the destination topic, message method and source party:
        destination_topic = msg.topic
        message_method = header.get("method")
        source_topic = header.get("from")

        # Dispatch the message.
        # Check case 2: COMMAND_ACKS. In this case, we don't check the source topic address, as we trust it's
        # originated by a device on this network that we contacted previously.
        if destination_topic == build_client_response_topic(
                self._cloud_creds.user_id, self._app_id
        ) and message_method in ["SETACK", "GETACK", "ERROR"]:
            _LOGGER.debug("This message is an ACK to a command this client has send.")

            # If the message is a PUSHACK/GETACK/ERROR, check if there is any pending command waiting for it and, if so,
            # resolve its future
            message_id = header.get("messageId")
            future = self._pending_messages_futures.get(message_id)
            if future is not None:
                _LOGGER.debug("Found a pending command waiting for response message")
                if message_method == "ERROR":
                    err = CommandError(error_payload=message.get('payload'))
                    if not self._loop.is_closed():
                        self._loop.call_soon_threadsafe(_handle_future, future, None, err)
                    else:
                        _LOGGER.warning("Could not return message %s to caller as the event loop has been closed already", message)
                elif message_method in ("SETACK", "GETACK"):
                    if not self._loop.is_closed():
                        self._loop.call_soon_threadsafe(
                            _handle_future, future, message, None
                        )  # future.set_exception
                    else:
                        _LOGGER.warning("Could not return message %s to caller as the event loop has been closed already", message)
                else:
                    _LOGGER.error(
                        f"Unhandled message method {message_method}. Please report it to the developer."
                        f"raw_msg: {msg}"
                    )
                del self._pending_messages_futures[message_id]
        # Check case 3: PUSH notification.
        # Again, here we don't check the source topic, we trust that's legitimate.
        elif (
                destination_topic == build_client_user_topic(self._cloud_creds.user_id)
                and message_method == "PUSH"
        ):
            namespace = header.get("namespace")
            payload = message.get("payload")
            origin_device_uuid = device_uuid_from_push_notification(source_topic)

            parsed_push_notification = parse_push_notification(
                namespace=namespace,
                message_payload=payload,
                originating_device_uuid=origin_device_uuid,
            )
            if parsed_push_notification is None:
                _LOGGER.error(
                    "Push notification parsing failed. That message won't be dispatched."
                )
            else:
                asyncio.run_coroutine_threadsafe(
                    self._handle_and_dispatch_push_notification(
                        parsed_push_notification
                    ),
                    loop=self._loop,
                )
        else:
            _LOGGER.warning(
                f"The current implementation of this library does not handle messages received on topic "
                f"({destination_topic}) and when the message method is {message_method}. "
                "If you see this message many times, it means Meross has changed the way its protocol "
                "works. Contact the developer if that happens!"
            )

    async def _async_dispatch_push_notification(
            self, push_notification: GenericPushNotification
    ) -> bool:
        handled = False
        # Lookup the originating device and deliver the push notification to that one.
        # Exclude subdevices: event dispatching among them is handled by their relative HUB.
        target_devs = self._device_registry.find_all_by(
            device_uuids=(push_notification.originating_device_uuid,),
            exclude_classes=(GenericSubDevice,)
        )
        dev = None

        if len(target_devs) < 1:
            _LOGGER.warning(
                f"Received a push notification ({push_notification.namespace}, "
                f"raw_data: {json.dumps(push_notification.raw_data)}) for device(s) "
                f"({push_notification.originating_device_uuid}) that "
                f"are not available in the local registry. Trigger a discovery to intercept those events."
            )

        if len(target_devs) > 0:
            # Pass the control to the specific device implementation
            for dev in target_devs:
                try:
                    handled = (
                            await dev.async_handle_push_notification(
                                namespace=push_notification.namespace,
                                data=push_notification.raw_data,
                            )
                            or handled
                    )
                except Exception as e:
                    _LOGGER.exception(
                        "An unhandled exception occurred while handling push notification"
                    )

        else:
            _LOGGER.warning(
                "Received a push notification for a device that is not available in the local registry. "
                "You may need to trigger a discovery to catch those updates. Device-UUID: "
                f"{push_notification.originating_device_uuid}"
            )

        return handled

    async def _async_handle_push_notification_post_dispatching(
            self, push_notification: GenericPushNotification
    ) -> bool:
        if isinstance(push_notification, UnbindPushNotification):
            _LOGGER.info(
                "Received an Unbind PushNotification. Releasing device resources..."
            )
            devs = self._device_registry.find_all_by(
                device_uuids=(push_notification.originating_device_uuid)
            )
            for d in devs:
                _LOGGER.info(f"Releasing resources for device {d.internal_id}")
                self._device_registry.relinquish_device(
                    device_internal_id=d.internal_id
                )
            return True
        return False

    async def _handle_and_dispatch_push_notification(
            self, push_notification: GenericPushNotification
    ) -> None:
        """
        This method runs within the event loop and is responsible for handling and dispatching push notifications
        to the relative meross device within the registry.

        :param push_notification:
        :return:
        """
        # Dispatching
        handled_device = await self._async_dispatch_push_notification(
            push_notification=push_notification
        )

        # Notify any listener that registered explicitly to push_notification
        target_devs = self._device_registry.find_all_by(
            device_uuids=(push_notification.originating_device_uuid,)
        )

        for handler in self._push_coros:
            try:
                await handler(push_notification, target_devs, self)
            except Exception as e:
                _LOGGER.exception(f"Uncaught error occurred while executing push notification "
                                  f"handler {handler} for {push_notification}")

        # Handling post-dispatching
        handled_post = await self._async_handle_push_notification_post_dispatching(
            push_notification=push_notification
        )

        if not (handled_device or handled_post):
            _LOGGER.warning(
                f"Uncaught push notification {push_notification.namespace}. "
                f"Raw data: {json.dumps(push_notification.raw_data)}"
            )

    async def async_execute_cmd(
            self,
            mqtt_hostname: str,
            mqtt_port: int,
            destination_device_uuid: str,
            method: str,
            namespace: Union[Namespace, str],
            payload: dict,
            timeout: float = DEFAULT_COMMAND_TIMEOUT,
            override_transport_mode: TransportMode = None
    ):
        """
        This method sends a command to the device, locally via HTTP or via the MQTT Meross broker.

        :param mqtt_hostname: the mqtt broker hostname
        :param mqtt_port: the mqtt broker port
        :param destination_device_uuid:
        :param method: Can be GET/SET
        :param namespace: Command namespace
        :param payload: A dict containing the payload to be sent
        :param timeout: Maximum time interval in seconds to wait for the command-answer
        :param override_transport_mode: when set, overrides the manager transport mode
        :return:
        """

        # Only attempt local http communication if enabled via configuration.
        transport_mode = override_transport_mode if override_transport_mode is not None else self._default_transport_mode
        attempt_lan = transport_mode == TransportMode.LAN_HTTP_FIRST or transport_mode == TransportMode.LAN_HTTP_FIRST_ONLY_GET and method.upper() == 'GET'
        if attempt_lan:
            # Check if the LocalIP is available for the given device
            device = self._device_registry.lookup_base_by_uuid(destination_device_uuid)
            if device is None:
                _LOGGER.debug("Cannot issue command via LAN (http) against device with uuid %s as the device is not yet available on the registry", destination_device_uuid)
                attempt_lan = False
            elif device.lan_ip is None:
                _LOGGER.debug("Cannot issue command via LAN (http) against device with uuid %s as the device has not reported any internal LAN ip.", destination_device_uuid)
                attempt_lan = False
            elif self._error_budget_manager.is_out_of_budget(destination_device_uuid):
                _LOGGER.debug("Cannot issue command via LAN (http) against device with uuid %s as the device has no more error budget left.", destination_device_uuid)
                attempt_lan = False
            if attempt_lan:
                try:
                    # In case we succeed here, return the data we got.
                    # Otherwise, try again with MQTT.
                    _LOGGER.debug("Sending %s-%s command via HTTP to %s via %s", method, str(namespace), destination_device_uuid, device.lan_ip)
                    return await self._async_execute_cmd_http(device_ip=device.lan_ip,destination_device_uuid=destination_device_uuid,method=method,namespace=namespace,payload=payload,timeout=min(timeout, 1.0))
                except Exception as e:
                    _LOGGER.exception("An error occurred while attempting to send a message over internal LAN to device %s. Retrying with MQTT transport.", destination_device_uuid)
                    self._error_budget_manager.notify_error(destination_device_uuid)

        # Retrieve the mqtt client for the given domain:port broker
        if self._override_mqtt_server is not None:
            _LOGGER.debug("Overriding MQTT host/port as per manager parameter")
            mqtt_hostname = self._override_mqtt_server[0]
            mqtt_port = self._override_mqtt_server[1]

        _LOGGER.debug("Sending %s-%s command via MQTT to %s via %s:%d", method, str(namespace), destination_device_uuid,
                      mqtt_hostname, mqtt_port)
        client = await self._async_get_create_mqtt_client(domain=mqtt_hostname, port=mqtt_port)
        return await self.async_execute_cmd_client(client=client,
                                                   destination_device_uuid=destination_device_uuid,
                                                   method=method,
                                                   namespace=namespace,
                                                   payload=payload,
                                                   timeout=timeout)

    async def _async_execute_cmd_http(self,
                                      device_ip: str,
                                      destination_device_uuid: str,
                                      method: str,
                                      namespace: Union[Namespace,str],
                                      payload: dict,
                                      timeout: float = 10.0):
        # Send the message over the network
        # Build the mqtt message we will send to the broker
        message, message_id = self._build_mqtt_message(method, namespace, payload, destination_device_uuid)

        async with ClientSession() as session:
            async with session.post(f"http://{device_ip}/config", json=json.loads(message.decode()), timeout=timeout) as response:
                data = await response.json()
                return data.get("payload")

    async def async_execute_cmd_client(self,
                                       client: mqtt.Client,
                                       destination_device_uuid: str,
                                       method: str,
                                       namespace: Namespace,
                                       payload: dict,
                                       timeout: float = 10.0):
        # Send the message over the network
        # Build the mqtt message we will send to the broker
        message, message_id = self._build_mqtt_message(method, namespace, payload, destination_device_uuid)

        # Create a future and perform the send/waiting to a task
        fut = self._loop.create_future()
        self._pending_messages_futures[message_id] = fut
        response = await self._async_send_and_wait_ack(
            client=client,
            future=fut,
            target_device_uuid=destination_device_uuid,
            message=message,
            timeout=timeout
        )
        return response.get("payload")

    async def _async_send_and_wait_ack(
            self, client: mqtt.Client, future: Future, target_device_uuid: str, message: bytes, timeout: float,
    ):
        if not client.is_connected():
            raise Exception("MQTT client not connected.")

        client.publish(
            topic=build_device_request_topic(target_device_uuid), payload=message
        )
        try:
            return await asyncio.wait_for(future, timeout)
        except TimeoutError as e:
            domain, port = self._get_client_from_domain_port(client=client)
            _LOGGER.error(
                "Timeout occurred while waiting a response for message %s sent to device uuid "
                "%s. Timeout was: %f seconds. Mqtt Host: %s:%d.",
                str(message), str(target_device_uuid), timeout, domain, port)
            raise CommandTimeoutError(message=str(message), target_device_uuid=target_device_uuid, timeout=timeout)
        except CommandError as e:
            domain, port = self._get_client_from_domain_port(client=client)
            _LOGGER.error(
                "Error occurred while waiting a response for message %s sent to device uuid "
                "%s. Mqtt Host: %s:%d. Returned error: %s",
                str(message), str(target_device_uuid), domain, port, e.error_payload)
            raise

    async def _notify_connection_drop(self):
        for d in self._device_registry.find_all_by():
            pushn = OnlinePushNotification(originating_device_uuid=d.uuid, raw_data={'online': {'status': -1}})
            await self._handle_and_dispatch_push_notification(pushn)

    def _build_mqtt_message(self, method: str, namespace: Union[Namespace, str], payload: dict, destination_device_uuid: str):
        """
        Sends a message to the Meross MQTT broker, respecting the protocol payload.

        :param method:
        :param namespace:
        :param payload:
        :param destination_device_uuid:

        :return:
        """

        # Generate a random 16 byte string
        randomstring = "".join(
            random.SystemRandom().choice(string.ascii_uppercase + string.digits)
            for _ in range(16)
        )

        # Hash it as md5
        md5_hash = md5()
        md5_hash.update(randomstring.encode("utf8"))
        messageId = md5_hash.hexdigest().lower()
        timestamp = int(round(time()))

        # Hash the messageId, the key and the timestamp
        md5_hash = md5()
        strtohash = "%s%s%s" % (messageId, self._cloud_creds.key, timestamp)
        md5_hash.update(strtohash.encode("utf8"))
        signature = md5_hash.hexdigest().lower()

        if not isinstance(namespace, Namespace) and not isinstance(namespace, str):
            raise ValueError("Namespace parameter must be a Namespace enum or a string.")
        namespace_val = namespace.value if isinstance(namespace, Namespace) else namespace

        data = {
            "header": {
                "from": self._client_response_topic,
                "messageId": messageId,  # Example: "122e3e47835fefcd8aaf22d13ce21859"
                "method": method,  # Example: "GET",
                "namespace": namespace_val,  # Example: "Appliance.System.All",
                "payloadVersion": 1,
                "sign": signature,  # Example: "b4236ac6fb399e70c3d61e98fcb68b74",
                "timestamp": timestamp,
                "triggerSrc": "Android",
                "uuid": destination_device_uuid
            },
            "payload": payload,
        }

        strdata = json.dumps(data,separators=(',', ':'))
        return strdata.encode("utf-8"), messageId

    def set_proxy(self, proxy_type, proxy_addr, proxy_port):
        self._enable_proxy = True
        self._proxy_type = proxy_type
        self._proxy_addr = proxy_addr
        self._proxy_port = proxy_port

        for k, client in self._mqtt_clients.items():
            _LOGGER.info("Setting proxy configuration for client %s...", k)
            client.proxy_set(proxy_type=self._proxy_type, proxy_addr=self._proxy_addr, proxy_port=self._proxy_port)
            client.reconnect()

    def dump_device_registry(self, filename):
        """
        Save the current list of devices into a file so that you can later re-load it without issuing
        a discovery. **Note**: the stored information might become out-of-date or unvalidated. For instance,
        a device name might change over time, as its online status or any other info that is not immutable (as the UUID).
        Use this with caution!
        """
        self._device_registry.dump_to_file(filename)

    def load_devices_from_dump(self, filename):
        """Reload the registry info from a dump. **Note**: this will override all the currently discovered devices."""
        self._device_registry.load_from_dump(filename, manager=self)


class DeviceRegistry(object):
    def __init__(self):
        self._devices_by_internal_id = {}

    def clear(self) -> None:
        """Clear all the registered devices"""
        ids = [devid for devid in self._devices_by_internal_id]
        for devid in ids:
            self.relinquish_device(devid)

    def dump_to_file(self, filename: str)->None:
        """Dump the current device list to a file"""
        dumped_base_devices = [{'abilities': x.abilities, 'info': x.cached_http_info.to_dict()} for x in self._devices_by_internal_id.values() if not isinstance(x, GenericSubDevice)]
        with open(filename, "wt") as f:
            json.dump(dumped_base_devices, f, default=lambda x: x.isoformat() if isinstance(x, datetime) else x.value if(isinstance(x,OnlineStatus)) else 'Not-Serializable')

    def load_from_dump(self, filename: str, manager: MerossManager) -> None:
        """Load the device registry from a file"""
        dumped_json_data = []
        with open(filename, "rt") as f:
            dumped_json_data = json.load(f)

        for deviced in dumped_json_data:
            device_abilities = deviced['abilities']
            device_info = HttpDeviceInfo.from_dict(deviced['info'])
            device = build_meross_device_from_abilities(http_device_info=device_info, device_abilities=device_abilities, manager=manager)
            self.enroll_device(device)

    def relinquish_device(self, device_internal_id: str):
        dev = self._devices_by_internal_id.get(device_internal_id)
        if dev is None:
            raise ValueError(
                f"Cannot relinquish device {device_internal_id} as it does not belong to this registry."
            )

        # Dismiss the device
        _LOGGER.debug(f"Disposing resources for {dev.name} ({dev.uuid})")
        dev.dismiss()
        del self._devices_by_internal_id[device_internal_id]
        _LOGGER.info(f"Device {dev.name} ({dev.uuid}) removed from registry")

    def enroll_device(self, device: BaseDevice):
        if device.internal_id in self._devices_by_internal_id:
            _LOGGER.info(
                f"Device {device.name} ({device.internal_id}) has been already added to the registry."
            )
            return
        else:
            _LOGGER.debug(
                f"Adding device {device.name} ({device.internal_id}) to registry."
            )
            self._devices_by_internal_id[device.internal_id] = device

    def lookup_by_id(self, device_id: str) -> Optional[BaseDevice]:
        return self._devices_by_internal_id.get(device_id)

    def lookup_base_by_uuid(self, device_uuid: str) -> Optional[BaseDevice]:
        res = list(
            filter(
                lambda d: d.uuid == device_uuid and not isinstance(d, GenericSubDevice),
                self._devices_by_internal_id.values(),
            )
        )
        if len(res) > 1:
            raise ValueError(f"Multiple devices found for device_uuid {device_uuid}")
        elif len(res) == 1:
            return res[0]
        else:
            return None

    def find_all_by(
            self,
            device_uuids: Optional[Iterable[str]] = None,
            internal_ids: Optional[Iterable[str]] = None,
            device_type: Optional[str] = None,
            device_class: Optional[Union[type, Iterable[type]]] = None,
            device_name: Optional[str] = None,
            online_status: Optional[OnlineStatus] = None,
            exclude_classes: Optional[Iterable[type]] = None
    ) -> List[BaseDevice]:

        def filter_by_type(dev: Any):
            for t in device_class:
                if isinstance(dev, t):
                    return True
            return False

        def filter_by_excluded_type(dev: Any):
            for t in exclude_classes:
                if isinstance(dev, t):
                    return False
            return True

        # Look by Internal UUIDs
        if internal_ids is not None:
            res = filter(
                lambda d: d.internal_id in internal_ids,
                self._devices_by_internal_id.values(),
            )
        else:
            res = self._devices_by_internal_id.values()

        if device_uuids is not None:
            res = filter(lambda d: d.uuid in device_uuids, res)
        if device_type is not None:
            res = filter(lambda d: d.type == device_type, res)
        if online_status is not None:
            res = filter(lambda d: d.online_status == online_status, res)
        if device_class is not None:
            if isinstance(device_class, type):
                res = filter(lambda d: isinstance(d, device_class), res)
            elif isinstance(device_class, Iterable):
                res = filter(filter_by_type, res)
        if device_name is not None:
            res = filter(lambda d: d.name == device_name, res)
        if exclude_classes is not None:
            res = filter(filter_by_excluded_type, res)

        return list(res)


def _handle_future(future: Future, result: object, exception: Exception):
    if future.cancelled():
        return

    if exception is not None:
        future.set_exception(exception)
    else:
        if future.cancelled():
            _LOGGER.debug("Skipping set_result for cancelled future.")
        elif future.done():
            _LOGGER.error("This future is already done: cannot set result.")
        else:
            future.set_result(result)


def set_future_done(future):
    if future in _PENDING_FUTURES:
        _PENDING_FUTURES.remove(future)


def _schedule_later(coroutine, start_delay, loop):
    async def delayed_execution(coro, delay, loop):
        await asyncio.sleep(delay=delay)
        await coro

    future = asyncio.run_coroutine_threadsafe(coro=delayed_execution(coro=coroutine, delay=start_delay, loop=loop),
                                              loop=loop)
    _PENDING_FUTURES.append(future)
    future.add_done_callback(set_future_done)
