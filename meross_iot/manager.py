from meross_iot.api import MerossHttpClient
from meross_iot.cloud.client import MerossCloudClient
from meross_iot.cloud.device_factory import build_wrapper
from threading import RLock


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
    _event_handlers = None
    _event_handlers_lock = None

    def __init__(self, meross_email, meross_password):
        self._devices_lock = RLock()
        self._devices = dict()
        self._event_handlers_lock = RLock()
        self._event_handlers = []

        self._http_client = MerossHttpClient(email=meross_email, password=meross_password)
        self._cloud_creds = self._http_client.get_cloud_credentials()

    def start(self):
        # Instantiate and start the mqtt cloud client
        self._cloud_client = MerossCloudClient(cloud_credentials=self._cloud_creds,
                                               push_message_callback=self._dispatch_push_notification)
        self._cloud_client.start()
        self._discover_devices()

    def stop(self):
        self._cloud_client.close()

    def register_event_handler(self, callback):
        with self._event_handlers_lock:
            if callback in self._event_handlers:
                pass
            else:
                self._event_handlers.append(callback)

    def unregister_event_handler(self, callback):
        with self._event_handlers_lock:
            if callback not in self._event_handlers:
                pass
            else:
                self._event_handlers.remove(callback)

    def get_device_by_uuid(self, uuid):
        dev = None
        with self._devices_lock:
            dev = self._devices.get(uuid)

        return dev

    def get_device_by_name(self, name):
        with self._devices_lock:
            for k, v in self._devices.items():
                if v.name.lower() == name.lower():
                    return v
        return None

    def get_supported_devices(self):
        return [x for k, x in self._devices.items()]

    def get_devices_by_kind(self, clazz):
        res = []
        with self._devices_lock:
            for k, v in self._devices.items():
                if isinstance(v, clazz):
                    res.append(v)
        return res

    def get_devices_by_type(self, type_name):
        res = []
        with self._devices_lock:
            for k, v in self._devices.items():
                if v.type.lower() == type_name.lower():
                    res.append(v)
        return res

    def _dispatch_push_notification(self, message):
        header = message['header']      # type: dict
        payload = message['payload']    # type: dict

        # Identify the UUID of the target device by looking at the FROM field of the message header
        dev_uuid = header['from'].split('/')[2]
        device = None
        with self._devices_lock:
            device = self._devices.get(dev_uuid)

        if device is not None:
            namespace = header['namespace']
            device.handle_push_notification(namespace, payload)
        else:
            # If we receive a push notification from a device that is not yet contained into our registry,
            # it probably means a new one has just been registered with the meross cloud.
            # Therefor, let's retrieve info from the HTTP api.
            self._discover_devices()

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
            self._handle_device_discovered(dev)

        return self._devices

    def _handle_device_discovered(self, dev):
        d_type = dev['deviceType']
        d_uuid = dev['uuid']
        device = build_wrapper(device_type=d_type, device_uuid=d_uuid, cloud_client=self._cloud_client,
                               device_specs=dev)

        if device is not None:
            # Check if the discovered device is already in the list of handled devices.
            # If not, add it right away. Otherwise, ignore it.
            is_new = False
            with self._devices_lock:
                if d_uuid not in self._devices:
                    is_new = True
                    new_dev = build_wrapper(cloud_client=self._cloud_client,
                                            device_type=d_type, device_uuid=d_uuid, device_specs=dev)
                    self._devices[d_uuid] = new_dev

            if is_new:
                # TODO: Notify a new device has been discovered!
                pass

