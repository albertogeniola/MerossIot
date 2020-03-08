from threading import RLock

from meross_iot.api import MerossHttpClient
from meross_iot.cloud.abilities import BIND, UNBIND, REPORT, ONLINE
from meross_iot.cloud.client import MerossCloudClient
from meross_iot.cloud.client_status import ClientStatus
from meross_iot.cloud.device_factory import build_wrapper, build_subdevice_wrapper
from meross_iot.cloud.devices.hubs import GenericHub
from meross_iot.logger import MANAGER_LOGGER as l
from threading import Thread, Event


class MerossManager(object):
    # HTTPClient object used to discover devices
    _http_client = None

    # Dictionary of devices that are currently handled by this manager
    # as UUID -> Device
    _devices = None

    # Lock item used to protect access to the device collection
    _devices_lock = None

    # Cloud credentials to be used against the Meross MQTT cloud
    _cloud_creds = None
    _cloud_client = None

    # List of callbacks that should be called when an event occurs
    _event_callbacks = None
    _event_callbacks_lock = None

    def __init__(self, meross_email, meross_password, discovery_interval=30.0):
        self._devices_lock = RLock()
        self._devices = dict()
        self._event_callbacks_lock = RLock()
        self._event_callbacks = []

        self._http_client = MerossHttpClient(email=meross_email, password=meross_password)
        self._cloud_creds = self._http_client.get_cloud_credentials()

        # Instantiate the mqtt cloud client
        self._cloud_client = MerossCloudClient(cloud_credentials=self._cloud_creds,
                                               push_message_callback=self._dispatch_push_notification)
        self._cloud_client.connection_status.register_connection_event_callback(callback=self._fire_event)
        self._device_discoverer = None
        self._stop_discovery = Event()
        self._device_discovery_done = Event()
        self._discovery_interval = discovery_interval

    def start(self, wait_for_first_discovery=True):
        l.debug("Starting manager")
        # Connect to the mqtt broker
        self._cloud_client.connect()
        l.debug("Connection succeeded. Starting discovery...")
        if self._device_discoverer is None or not self._device_discoverer.is_alive():
            self._device_discoverer = Thread(target=self._device_discover_thread)
            self._device_discoverer.start()

        if wait_for_first_discovery:
            l.debug("Caller requested wait-for-first-discovery. Waiting...")
            self._device_discovery_done.wait()
        l.debug("Discovery done.")

    def stop(self):
        l.debug("Stopping manager...")
        self._cloud_client.close()
        self._stop_discovery.set()
        self._device_discoverer.join()

        l.debug("Stop done.")

    def _device_discover_thread(self):
        while True:
            try:
                self._discover_devices(online_only=False)
            finally:
                if self._stop_discovery.wait(self._discovery_interval):
                    self._stop_discovery.clear()
                    break

    def register_event_handler(self, callback):
        with self._event_callbacks_lock:
            if callback in self._event_callbacks:
                pass
            else:
                self._event_callbacks.append(callback)

    def unregister_event_handler(self, callback):
        with self._event_callbacks_lock:
            if callback not in self._event_callbacks:
                pass
            else:
                self._event_callbacks.remove(callback)

    def get_device_by_uuid(self, uuid):
        self._ensure_started()

        dev = None
        with self._devices_lock:
            dev = self._devices.get(uuid)

        return dev

    def get_device_by_name(self, name):
        self._ensure_started()

        with self._devices_lock:
            for k, v in self._devices.items():
                if v.name.lower() == name.lower():
                    return v
        return None

    def get_supported_devices(self):
        self._ensure_started()
        return [x for k, x in self._devices.items()]

    def get_devices_by_kind(self, clazz):
        self._ensure_started()
        res = []
        with self._devices_lock:
            for k, v in self._devices.items():
                if isinstance(v, clazz):
                    res.append(v)
        return res

    def get_devices_by_type(self, type_name):
        self._ensure_started()
        res = []
        with self._devices_lock:
            for k, v in self._devices.items():
                if v.type.lower() == type_name.lower():
                    res.append(v)
        return res

    def _dispatch_push_notification(self, message, from_myself=False):
        """
        When a push notification is received from the MQTT client, it needs to be delivered to the
        corresponding device. This method serves that scope.
        :param message:
        :param from_myself: boolean flag. When True, it means that the message received is related to a
        previous request issued by this client. When is false, it means the message is related to some other
        client.
        :return:
        """
        header = message['header']      # type: dict
        payload = message['payload']    # type: dict

        # Identify the UUID of the target device by looking at the FROM field of the message header
        dev_uuid = header['from'].split('/')[2]

        # Let's intercept the Bind events: they are useful to trigger new device discovery
        namespace = header.get('namespace')
        if namespace is not None and namespace in [BIND, ONLINE]:
            self._discover_devices()

        # Let's find the target of the event so that it can handle accordingly
        device = None
        with self._devices_lock:
            device = self._devices.get(dev_uuid)

        if device is not None:
            device.handle_push_notification(namespace, payload, from_myself=from_myself)
        else:
            # If we receive a push notification from a device that is not yet contained into our registry,
            # it probably means a new one has just been registered with the meross cloud.
            # This should never happen as we handle the "bind" event just above. However, It appears that the report
            # event is fired before the BIND event. So we need to ignore it at this point
            if namespace == REPORT:
                l.info("Ignoring REPORT event from device %s" % dev_uuid)
            else:
                l.warn("An event was received from an unknown device, which did not trigger the BIND event. "
                       "Device UUID: %s, namespace: %s." % (dev_uuid, namespace))

    def _discover_devices(self, online_only=False):
        """
        Discovers the devices that are visible via HTTP API and update the internal list of
        managed devices accordingly.
        :return:
        """
        for dev in self._http_client.list_devices():
            online = dev['onlineStatus']

            if online_only and online != 1:
                # The device is not online, so we skip it.
                continue

            # If the device we have discovered is not in the list we already handle, we need to add it.
            discovered = self._handle_device_discovered(dev)

            # If the specific device is an HUB, add all its sub devices
            if isinstance(discovered, GenericHub):
                for subdev in self._http_client.list_hub_subdevices(discovered.uuid):
                    self._handle_device_discovered(dev=subdev, parent_hub=discovered)

        self._device_discovery_done.set()

        return self._devices

    def _handle_device_unbound(self, dev_uuid):
        with self._devices_lock:
            if dev_uuid in self._devices:
                l.info("Unregistering device %s" % dev_uuid)
                del self._devices[dev_uuid]

    def _handle_device_discovered(self, dev, parent_hub=None):
        device = None

        # Check whether we are dealing with a full device or with a subdevice
        if 'deviceType' in dev and 'uuid' in dev:
            # FULL DEVICE case
            d_type = dev['deviceType']
            d_id = dev['uuid']
            device_id = d_id
            device = build_wrapper(device_type=d_type, device_uuid=d_id,
                                   cloud_client=self._cloud_client, device_specs=dev)
            is_subdevice = False

        elif 'subDeviceType' in dev and 'subDeviceId' in dev:
            # SUB DEVICE case
            d_type = dev['subDeviceType']
            d_id = dev['subDeviceId']
            device_id = "%s:%s" % (parent_hub.uuid, d_id)
            device = build_subdevice_wrapper(device_type=d_type, device_id=d_id, parent_hub=parent_hub,
                                   cloud_client=self._cloud_client, device_specs=dev)
            is_subdevice = True

        else:
            l.warn("Discovered device does not seem to be either a full device nor a subdevice.")
            return

        if device is not None:
            # Check if the discovered device is already in the list of handled devices.
            # If not, add it right away. Otherwise, ignore it.
            is_new = False
            with self._devices_lock:
                if device_id not in self._devices:
                    is_new = True
                    self._devices[device_id] = device

            # If this is new device, register the event handler for it and fire the ONLINE event.
            if is_new:
                with self._event_callbacks_lock:
                    for c in self._event_callbacks:
                        device.register_event_callback(c)

            # Otherwise, fire an OFFLINE event if the device online status has changed
            else:
                old_dev = self._devices.get(device_id)
                new_online_status = dev.get('onlineStatus', 2)

                # TODO: Fix this workaround...
                #  Emulate the push notification
                payload = {'online': {'status': new_online_status}}
                old_dev.handle_push_notification(ONLINE, payload)

            # TODO: handle subdevices
        return device

    def _fire_event(self, eventobj):
        for c in self._event_callbacks:
            try:
                c(eventobj)
            except:
                l.exception("An unhandled error occurred while invoking callback")

    def _ensure_started(self):
        if not self._cloud_client.connection_status.check_status(ClientStatus.SUBSCRIBED):
            l.warn("The manager is not connected to the mqtt broker. Did you start the Meross manager?")
