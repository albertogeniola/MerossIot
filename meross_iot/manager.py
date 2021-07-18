import asyncio
import json
import logging
import random
import ssl
import string
import sys
from asyncio import Future, AbstractEventLoop
from asyncio import TimeoutError
from hashlib import md5
from time import time
from typing import Optional, List, TypeVar, Iterable, Callable, Awaitable, Tuple

import paho.mqtt.client as mqtt

from meross_iot.controller.device import BaseDevice, HubDevice, GenericSubDevice
from meross_iot.device_factory import (
    build_meross_device_from_abilities,
    build_meross_subdevice,
    build_meross_device_from_known_types,
)
from meross_iot.http_api import MerossHttpClient
from meross_iot.model.constants import DEFAULT_MQTT_PORT
from meross_iot.model.enums import Namespace, OnlineStatus
from meross_iot.model.exception import (
    CommandTimeoutError,
    CommandError,
    RateLimitExceeded,
    UnknownDeviceType
)
from meross_iot.model.http.device import HttpDeviceInfo
from meross_iot.model.http.subdevice import HttpSubdeviceInfo
from meross_iot.model.push.factory import parse_push_notification
from meross_iot.model.push.generic import GenericPushNotification
from meross_iot.model.push.online import OnlinePushNotification
from meross_iot.model.push.unbind import UnbindPushNotification
from meross_iot.utilities.limiter import (
    RateLimitChecker,
    RateLimitResult,
    RateLimitResultStrategy,
)
from meross_iot.utilities.mqtt import (
    generate_mqtt_password,
    generate_client_and_app_id,
    build_client_response_topic,
    build_client_user_topic,
    verify_message_signature,
    device_uuid_from_push_notification,
    build_device_request_topic,
)

logging.basicConfig(
    format="%(levelname)s:%(message)s", level=logging.INFO, stream=sys.stdout
)
_LOGGER = logging.getLogger(__name__)

_CONNECTION_DROP_UPDATE_SCHEDULE_INTERVAL = 2

T = TypeVar("T", bound=BaseDevice)  # Declare type variable


def _mqtt_key_from_domain_port(domain: str, port: int) -> str:
    return f"{domain}:{port}"


class MerossManager(object):
    """
    This class implements a full-features Meross Client, which provides device discovery and registry.
    *Note*: The manager must be initialized before invoking any of its discovery/registry methods. As soon as
    you create a manager, you shoul call :meth:`async_init`!
    """

    def __init__(
            self,
            http_client: MerossHttpClient,
            auto_reconnect: Optional[bool] = True,
            mqtt_skip_cert_validation: bool = False,
            ca_cert: Optional[str] = None,
            rate_limiter: Optional[RateLimitChecker] = None,
            loop: Optional[AbstractEventLoop] = None,
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
        :param rate_limiter: (Optional) Rate limiter
        :param loop: (Optional) Asyncio loop to use
        :param args:
        :param kwords:
        """

        # Store local attributes
        self.__started = False
        self.__stop_requested = False
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
        self._limiter = rate_limiter

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

        if not client.is_connected():
            conn_evt = self._mqtt_connected_and_subscribed.get(dict_key)  # type: asyncio.Event
            if conn_evt is None:
                conn_evt = asyncio.Event(loop=self._loop)
                client.connect(host=domain, port=port, keepalive=30)
                self._mqtt_connected_and_subscribed[dict_key] = conn_evt

            await conn_evt.wait()

        return client

    def _new_mqtt_client(self) -> mqtt.Client:
        # Setup mqtt client
        client = mqtt.Client(client_id=self._client_id, protocol=mqtt.MQTTv311)
        client.username_pw_set(username=self._cloud_creds.user_id, password=self._mqtt_password)

        # Certificate validation setup
        client.tls_set(
            ca_certs=self._ca_cert,
            certfile=None,
            keyfile=None,
            cert_reqs=ssl.CERT_NONE if self._mqtt_skip_validation else ssl.CERT_REQUIRED,
            tls_version=ssl.PROTOCOL_TLS,
            ciphers=None,
        )
        client.tls_insecure_set(self._mqtt_skip_validation)

        # Setup Callbacks
        client.on_connect = self._on_connect
        client.on_message = self._on_message
        client.on_disconnect = self._on_disconnect
        client.on_subscribe = self._on_subscribe

        return client

    @property
    def limiter(self) -> RateLimitChecker:
        return self._limiter

    @limiter.setter
    def limiter(self, limiter: RateLimitChecker):
        self._limiter = limiter

    def register_push_notification_handler_coroutine(
            self, coro: Callable[[GenericPushNotification, List[BaseDevice]], Awaitable]
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
            self, coro: Callable[[GenericPushNotification, List[BaseDevice]], Awaitable]
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
        if self.__stop_requested:
            _LOGGER.warning("Manager already stopping/stopped")
            return

        _LOGGER.info("Manager stop requested.")
        self.__stop_requested = True

    def find_devices(
            self,
            device_uuids: Optional[Iterable[str]] = None,
            internal_ids: Optional[Iterable[str]] = None,
            device_type: Optional[str] = None,
            device_class: Optional[type] = None,
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
        :param device_class: Filter based on the resulting device class. You can filter also for capability Mixins,
            such as :code:`meross_iot.controller.mixins.toggle.ToggleXMixin` (returns all the devices supporting
            ToggleX capability) or :code:`meross_iot.controller.mixins.light.LightMixin`
            (returns all the device that supports light control).
            You can also identify all the HUB devices by specifying :code:`meross_iot.controller.device.HubDevice`,
            Sensors as :code:`meross_iot.controller.subdevice.Ms100Sensor` and Valves as
            Sensors as :code:`meross_iot.controller.subdevice.Mts100v3Valve`.
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

    async def _async_loop(self) -> None:
        """
        Looper logic
        """
        _LOGGER.info("Starting Manager Looper")
        processed_loops = 0
        while not self.__stop_requested:
            # Loop over a copy of the dictionary to prevent dictionary changes while running
            for key, client in {k: v for k, v in self._mqtt_clients.items() if v}.items():
                # Process 100ms every loop
                await self._loop.run_in_executor(None, client.loop, 0.1)
                processed_loops += 1

            # In case there is nothing to do, wait a bit
            if processed_loops < 1:
                await asyncio.sleep(.1)

        _LOGGER.debug("Stop flag raised, ending loop")

    async def async_device_discovery(
            self, update_subdevice_status: bool = True, meross_device_uuid: str = None
    ) -> Iterable[BaseDevice]:
        """
        Fetch devices and online status from HTTP API. This method also notifies/updates local device online/offline
        status.

        :param meross_device_uuid: Meross UUID of the device that the user wants to discover (is already known).
        This parameter restricts the discovery only to that particular device. When None, all the devices
        reported by the HTTP api will be discovered.
        :param update_subdevice_status: When True, tells the manager to retrieve the HUB status in order to update
        hub-subdevice online status, which would be UNKNOWN if not explicitly retrieved.

        :return: A list of discovered device, which implement `BaseDevice`
        """
        _LOGGER.info(
            f"\n\n------- Triggering HTTP discovery, filter_device: {meross_device_uuid} -------"
        )
        # List http devices
        http_devices = await self._http_client.async_list_devices()

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
        _LOGGER.info(
            f"The following devices were already known to me: {already_known_http_devices}"
        )
        _LOGGER.info(
            f"The following devices are new to me: {discovered_new_http_devices}"
        )

        # For every newly discovered device, retrieve its abilities and then build a corresponding wrapper.
        # In the meantime, update state of the already known devices
        # Do this in "parallel" with multiple tasks rather than executing every task singularly
        tasks = []
        for d in discovered_new_http_devices:
            tasks.append(self._loop.create_task(self._async_enroll_new_http_dev(d)))
        for hdevice, ldevice in already_known_http_devices.items():
            tasks.append(
                self._loop.create_task(ldevice.update_from_http_state(hdevice))
            )

        _LOGGER.info(
            f"Updating {len(already_known_http_devices)} known devices form HTTPINFO and fetching "
            f"data from {len(discovered_new_http_devices)} newly discovered devices..."
        )
        # Wait for factory to build all devices
        enrolled_devices = await asyncio.gather(*tasks, loop=self._loop)
        _LOGGER.info(f"Fetch and update done")

        # Let's now handle HubDevices. For every HubDevice we have, we need to fetch new possible subdevices
        # from the HTTP API
        subdevtasks = []
        hubs = []
        for d in enrolled_devices:
            if isinstance(d, HubDevice):
                hubs.append(d)
                subdevs = await self._http_client.async_list_hub_subdevices(
                    hub_id=d.uuid
                )
                for sd in subdevs:
                    subdevtasks.append(
                        self._loop.create_task(
                            self._async_enroll_new_http_subdev(
                                subdevice_info=sd,
                                hub=d,
                                hub_reported_abilities=d.abilities,
                            )
                        )
                    )
        # Wait for factory to build all devices
        enrolled_subdevices = await asyncio.gather(*subdevtasks, loop=self._loop)

        # We need to update the state of hubs in order to refresh subdevices online status
        if update_subdevice_status:
            for h in hubs:
                await h.async_update(drop_on_overquota=False)
        _LOGGER.info(f"\n------- HTTP discovery ended -------\n")

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
        Starts the looper logic
        """
        if self.__started:
            raise RuntimeError("Async started was already called")
        if self.__stop_requested:
            raise RuntimeError("This managed has been marked for stop and is still stopping")

        def reset_started_flag(_fut):
            self.__started = False

        _LOGGER.info("Starting looper task")
        self._mqtt_looper_task = self._loop.create_task(self._async_loop()).add_done_callback(reset_started_flag)

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
                    mqtt_hostname=device_info.domain,
                    mqtt_port=DEFAULT_MQTT_PORT
                )
                abilities = res_abilities.get("ability")
            except CommandTimeoutError:
                _LOGGER.warning(
                    f"Device {device_info.dev_name} ({device_info.uuid}) is online, but timeout occurred "
                    f"when fetching its abilities."
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
                _LOGGER.warning(
                    f"Device {device_info.dev_name} ({device_info.uuid}) was built statically via known "
                    f"types, because we failed to retrieve updated abilities for the given device."
                )
            except UnknownDeviceType:
                _LOGGER.error(
                    f"Could not build statically device {device_info.dev_name} ({device_info.uuid}) as it's not a known type."
                )

        # Enroll the device
        if device is not None:
            self._device_registry.enroll_device(device)
            return device

    def _on_connect(self, client, userdata, rc, other):
        # NOTE! This method is called by the paho-mqtt thread, thus any invocation to the
        # asyncio platform must be scheduled via `self._loop.call_soon_threadsafe()` method.

        _LOGGER.debug(f"Connected with result code {rc}")
        # Subscribe to the relevant topics
        _LOGGER.debug("Subscribing to topics...")
        client.subscribe(
            [(self._user_topic, 1), (self._client_response_topic, 1)]
        )

    def _on_disconnect(self, client: mqtt.Client, userdata, rc):
        # NOTE! This method is called by the paho-mqtt thread, thus any invocation to the
        # asyncio platform must be scheduled via `self._loop.call_soon_threadsafe()` method.
        _LOGGER.info("Disconnection detected. Reason: %s" % str(rc))

        if rc == mqtt.MQTT_ERR_SUCCESS:
            pass
        else:
            # Otherwise, if the disconnection was not intentional, we probably had a connection drop.
            # In this case, we only stop the loop thread if auto_reconnect is not set. In fact, the loop will
            # handle reconnection autonomously on connection drops.
            if self._auto_reconnect:
                _LOGGER.info("Reconnecting (auto_reconnect flag has been set)")
                client.reconnect()
            else:
                _LOGGER.info("No reconnection will be attempted as auto_reconnect flag was not set")
                del self._mqtt_connected_and_subscribed[userdata]

        # When a disconnection occurs, we need to set "unavailable" status.
        asyncio.run_coroutine_threadsafe(
            self._notify_connection_drop(), loop=self._loop
        )

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

        async def update_and_trigger_online_event(dev: BaseDevice):
            prev_status = dev.online_status
            await dev.async_update(drop_on_overquota=False)
            if dev.online_status != prev_status:
                await dev.async_handle_push_notification(namespace=Namespace.SYSTEM_ONLINE, data={'online': {'status': dev.online_status.value}})

        i = 0
        for d in self.find_devices():
            _schedule_later(
                coroutine=update_and_trigger_online_event(d),
                start_delay=i,
                loop=self._loop,
            )
            i += _CONNECTION_DROP_UPDATE_SCHEDULE_INTERVAL

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
                    err = CommandError(error_payload=message.payload)
                    self._loop.call_soon_threadsafe(_handle_future, future, None, err)
                elif message_method in ("SETACK", "GETACK"):
                    self._loop.call_soon_threadsafe(
                        _handle_future, future, message, None
                    )  # future.set_exception
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
        target_devs = self._device_registry.find_all_by(
            device_uuids=(push_notification.originating_device_uuid,)
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

        try:
            for handler in self._push_coros:
                await handler(
                    push_notification=push_notification, target_devices=target_devs
                )
        except Exception as e:
            _LOGGER.exception(
                f"An error occurred while executing push notification handling for {push_notification}"
            )

        # Handling post-dispatching
        handled_post = await self._async_handle_push_notification_post_dispatching(
            push_notification=push_notification
        )

        if not (handled_device or handled_post):
            _LOGGER.warning(
                f"Uncaught push notification {push_notification.namespace}. "
                f"Raw data: {json.dumps(push_notification.raw_data)}"
            )

    def _api_rate_limit_checks(self, destination_device_uuid: str) -> Tuple[RateLimitResultStrategy, float]:
        if self._limiter is None:
            return RateLimitResultStrategy.PerformCall, 0
        else:
            return self._limiter.check_limits(device_uuid=destination_device_uuid)

    async def async_execute_cmd(
            self,
            mqtt_hostname: str,
            mqtt_port: int,
            destination_device_uuid: str,
            method: str,
            namespace: Namespace,
            payload: dict,
            timeout: float = 10.0,
            skip_rate_limiting_check: bool = False,
            drop_on_overquota: bool = True,
    ):
        """
        This method sends a command to the MQTT Meross broker.

        :param mqtt_hostname: the mqtt broker hostname
        :param mqtt_port: the mqtt broker port
        :param destination_device_uuid:
        :param method: Can be GET/SET
        :param namespace: Command namespace
        :param payload: A dict containing the payload to be sent
        :param timeout: Maximum time interval in seconds to wait for the command-answer
        :param skip_rate_limiting_check: When True, no API rate limit is performed for executing the command
        :param drop_on_overquota: When True, API calls that hit the overquota limit will be dropped.
                                  If set to False, those calls will not be dropped, but delayed accordingly.
        :return:
        """
        # Retrieve the mqtt client for the given domain:port broker
        client = await self._async_get_create_mqtt_client(domain=mqtt_hostname, port=mqtt_port)
        return await self.async_execute_cmd_client(client=client,
                                                   destination_device_uuid=destination_device_uuid,
                                                   method=method,
                                                   namespace=namespace,
                                                   payload=payload,
                                                   timeout=timeout,
                                                   skip_rate_limiting_check=skip_rate_limiting_check,
                                                   drop_on_overquota=drop_on_overquota)

    async def async_execute_cmd_client(self,
                                       client: mqtt.Client,
                                       destination_device_uuid: str,
                                       method: str,
                                       namespace: Namespace,
                                       payload: dict,
                                       timeout: float = 10.0,
                                       skip_rate_limiting_check: bool = False,
                                       drop_on_overquota: bool = True, ):
        # TODO: Document this method
        # Check rate limits
        if not skip_rate_limiting_check:
            rate_limiting_action, time_to_wait = self._api_rate_limit_checks(
                destination_device_uuid=destination_device_uuid
            )
            if rate_limiting_action == RateLimitResultStrategy.PerformCall:
                pass
            elif (
                    rate_limiting_action == RateLimitResultStrategy.DelayCall
                    or rate_limiting_action == RateLimitResultStrategy.DropCall
                    and not drop_on_overquota
            ):
                await asyncio.sleep(delay=time_to_wait, loop=self._loop)
                return await self.async_execute_cmd_client(
                    client=client,
                    destination_device_uuid=destination_device_uuid,
                    method=method,
                    namespace=namespace,
                    payload=payload,
                    timeout=timeout,
                )
            elif rate_limiting_action == RateLimitResultStrategy.DropCall:
                raise RateLimitExceeded()
            else:
                raise ValueError("Unsupported rate-limiting action")

        # Send the message over the network
        # Build the mqtt message we will send to the broker
        message, message_id = self._build_mqtt_message(method, namespace, payload)

        # Create a future and perform the send/waiting to a task
        fut = self._loop.create_future()
        self._pending_messages_futures[message_id] = fut

        response = await self._async_send_and_wait_ack(
            client=client,
            future=fut,
            target_device_uuid=destination_device_uuid,
            message=message,
            timeout=timeout,
        )
        return response.get("payload")

    async def _async_send_and_wait_ack(
            self, client: mqtt.Client, future: Future, target_device_uuid: str, message: bytes, timeout: float
    ):
        message_info = client.publish(
            topic=build_device_request_topic(target_device_uuid), payload=message
        )
        try:
            return await asyncio.wait_for(future, timeout, loop=self._loop)
        except TimeoutError as e:
            _LOGGER.error(
                f"Timeout occurred while waiting a response for message {message} sent to device uuid "
                f"{target_device_uuid}. Timeout was: {timeout} seconds."
            )
            raise CommandTimeoutError()

    async def _notify_connection_drop(self):
        for d in self._device_registry.find_all_by():
            pushn = OnlinePushNotification(originating_device_uuid=d.uuid, raw_data={'online': {'status': -1}})
            await self._handle_and_dispatch_push_notification(pushn)

    def _build_mqtt_message(self, method: str, namespace: Namespace, payload: dict):
        """
        Sends a message to the Meross MQTT broker, respecting the protocol payload.

        :param method:
        :param namespace:
        :param payload:

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

        data = {
            "header": {
                "from": self._client_response_topic,
                "messageId": messageId,  # Example: "122e3e47835fefcd8aaf22d13ce21859"
                "method": method,  # Example: "GET",
                "namespace": namespace.value,  # Example: "Appliance.System.All",
                "payloadVersion": 1,
                "sign": signature,  # Example: "b4236ac6fb399e70c3d61e98fcb68b74",
                "timestamp": timestamp
            },
            "payload": payload,
        }
        strdata = json.dumps(data)
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


class DeviceRegistry(object):
    def __init__(self):
        self._devices_by_internal_id = {}

    def relinquish_device(self, device_internal_id: str):
        dev = self._devices_by_internal_id.get(device_internal_id)
        if dev is None:
            raise ValueError(
                f"Cannot relinquish device {device_internal_id} as it does not belong to this registry."
            )

        # Dismiss the device
        # TODO: implement the dismiss() method to release device-held resources
        _LOGGER.debug(f"Disposing resources for {dev.name} ({dev.uuid})")
        dev.dismiss()
        del self._devices_by_internal_id[device_internal_id]
        _LOGGER.info(f"Device {dev.name} ({dev.uuid}) removed from registry")

    def enroll_device(self, device: BaseDevice):
        if device.internal_id in self._devices_by_internal_id:
            _LOGGER.warning(
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
            device_class: Optional[T] = None,
            device_name: Optional[str] = None,
            online_status: Optional[OnlineStatus] = None,
    ) -> List[BaseDevice]:

        # Look by Interonnal UUIDs
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
            res = filter(lambda d: isinstance(d, device_class), res)
        if device_name is not None:
            res = filter(lambda d: d.name == device_name, res)

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


def _schedule_later(coroutine, start_delay, loop):
    async def delayed_execution(coro, delay, loop):
        await asyncio.sleep(delay=delay, loop=loop)
        await coro

    asyncio.ensure_future(
        delayed_execution(coro=coroutine, delay=start_delay, loop=loop), loop=loop
    )
