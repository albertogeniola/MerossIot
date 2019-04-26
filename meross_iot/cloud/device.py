from abc import ABC, abstractmethod
from threading import RLock
from meross_iot.cloud.timeouts import LONG_TIMEOUT
from meross_iot.cloud.abilities import ONLINE, WIFI_LIST, TRACE, DEBUG
from meross_iot.logger import DEVICE_LOGGER as l


class AbstractMerossDevice(ABC):
    # Device status + lock to protect concurrent access
    _state_lock = None
    online = False

    # Device info and connection parameters
    uuid = None
    app_id = None
    name = None
    type = None
    hwversion = None
    fwversion = None

    # Cached list of abilities
    _abilities = None

    # Cloud client: the object that handles mqtt communication with the Meross Cloud
    _cloud_client = None

    def __init__(self, cloud_client, device_uuid, **kwargs):
        self._cloud_client = cloud_client
        self._state_lock = RLock()

        self.uuid = device_uuid

        if "channels" in kwargs:
            self._channels = kwargs['channels']

        # Information about device
        if "devName" in kwargs:
            self.name = kwargs['devName']
        if "deviceType" in kwargs:
            self.type = kwargs['deviceType']
        if "fmwareVersion" in kwargs:
            self.fwversion = kwargs['fmwareVersion']
        if "hdwareVersion" in kwargs:
            self.hwversion = kwargs['hdwareVersion']
        if "onlineStatus" in kwargs:
            self.online = kwargs['onlineStatus'] == 1

    def device_id(self):
        return self._uuid

    def handle_push_notification(self, namespace, payload):
        # Handle the ONLINE push notification
        # Leave the rest to the specific implementation
        if namespace == ONLINE:
            status = payload['online']['status']
            if status == 2:
                with self._state_lock:
                    self.online = False
            elif status == 1:
                with self._state_lock:
                    self.online = True
            else:
                l.error("Unknown online status has been reported from the device: %d" % status)

        else:
            self._handle_push_notification(namespace, payload)

    @abstractmethod
    def _handle_push_notification(self, namespace, payload):
        """
        Handles push messages for this device. This method should be implemented by the base class in order
        to catch status changes issued by other clients (i.e. the Meross app on the user's device).
        :param namespace:
        :param message:
        :return:
        """
        pass

    @abstractmethod
    def get_status(self):
        pass

    def get_sys_data(self):
        return self._cloud_client.execute_cmd(self.uuid, "GET", "Appliance.System.All", {})

    def get_abilities(self):
        # TODO: Make this cached value expire after a bit...
        if self._abilities is None:
            self._abilities = self._cloud_client.execute_cmd(self.uuid, "GET", "Appliance.System.Ability", {})['ability']
        return self._abilities

    def get_report(self):
        return self._cloud_client.execute_cmd(self.uuid, "GET", "Appliance.System.Report", {})

    def get_wifi_list(self):
        if WIFI_LIST in self.get_abilities():
            return self._cloud_client.execute_cmd(self.uuid, "GET", WIFI_LIST, {}, timeout=LONG_TIMEOUT)
        else:
            l.error("This device does not support the WIFI_LIST ability")
            return None

    def get_trace(self):
        if TRACE in self.get_abilities():
            return self._cloud_client.execute_cmd(self.uuid, "GET", TRACE, {})
        else:
            l.error("This device does not support the TRACE ability")
            return None

    def get_debug(self):
        if DEBUG in self.get_abilities():
            return self._cloud_client.execute_cmd(self.uuid, "GET", DEBUG, {})
        else:
            l.error("This device does not support the DEBUG ability")
            return None