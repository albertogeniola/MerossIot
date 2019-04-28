from abc import ABC, abstractmethod
from threading import RLock

from meross_iot.cloud.exceptions.OfflineDeviceException import OfflineDeviceException
from meross_iot.cloud.timeouts import LONG_TIMEOUT, SHORT_TIMEOUT
from meross_iot.cloud.abilities import ONLINE, WIFI_LIST, TRACE, DEBUG, ABILITY, REPORT, ALL
from meross_iot.logger import DEVICE_LOGGER as l
from meross_iot.meross_event import DeviceOnlineStatusEvent


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
    __cloud_client = None

    # Data structure for firing events.
    __event_handlers_lock = None
    __event_handlers = None

    def __init__(self, cloud_client, device_uuid, **kwargs):
        self.__cloud_client = cloud_client
        self._state_lock = RLock()
        self.__event_handlers_lock = RLock()
        self.__event_handlers = []

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

    def handle_push_notification(self, namespace, payload, from_myself=False):
        # Handle the ONLINE push notification
        # Leave the rest to the specific implementation
        if namespace == ONLINE:
            old_online_status = self.online
            status = payload['online']['status']
            if status == 2:
                with self._state_lock:
                    self.online = False
            elif status == 1:
                with self._state_lock:
                    self.online = True
            else:
                l.error("Unknown online status has been reported from the device: %d" % status)

            # If the online status changed, fire the corresponding event
            if old_online_status != self.online:
                evt = DeviceOnlineStatusEvent(self, self.online)
                self.fire_event(evt)
        else:
            self._handle_push_notification(namespace, payload, from_myself=from_myself)

    def register_event_callback(self, callback):
        with self.__event_handlers_lock:
            if callback not in self.__event_handlers:
                self.__event_handlers.append(callback)
            else:
                l.debug("The callback you tried to register is already present.")
                pass

    def unregister_event_callback(self, callback):
        with self.__event_handlers_lock:
            if callback in self.__event_handlers:
                self.__event_handlers.remove(callback)
            else:
                l.debug("The callback you tried to unregister is not present.")
                pass

    def fire_event(self, eventobj):
        for c in self.__event_handlers:
            try:
                c(eventobj)
            except:
                l.exception("Unhandled error occurred while executing the registered event-callback")

    @abstractmethod
    def _handle_push_notification(self, namespace, payload, from_myself=False):
        """
        Handles push messages for this device. This method should be implemented by the base class in order
        to catch status changes issued by other clients (i.e. the Meross app on the user's device).
        :param namespace:
        :param message:
        :param from_myself: boolean flag. When true, it means that the notification is generated in response to a
        command that was issued by this client. When false, it means that another client generated the event.
        :return:
        """
        pass

    @abstractmethod
    def get_status(self):
        pass

    def execute_command(self, command, namespace, payload, callback=None, timeout=SHORT_TIMEOUT):
        with self._state_lock:
            # If the device is not online, what's the point of issuing the command?
            if not self.online:
                raise OfflineDeviceException("The device %s (%s) is offline. The command cannot be executed" %
                                             (self.name, self.uuid))

        return self.__cloud_client.execute_cmd(self.uuid, command, namespace, payload, callback=callback, timeout=timeout)

    def get_sys_data(self):
        return self.execute_command("GET", ALL, {})

    def get_abilities(self):
        # TODO: Make this cached value expire after a bit...
        if self._abilities is None:
            self._abilities = self.execute_command("GET", ABILITY, {})['ability']
        return self._abilities

    def get_report(self):
        return self.execute_command("GET", REPORT, {})

    def get_wifi_list(self):
        if WIFI_LIST in self.get_abilities():
            return self.execute_command("GET", WIFI_LIST, {}, timeout=LONG_TIMEOUT)
        else:
            l.error("This device does not support the WIFI_LIST ability")
            return None

    def get_trace(self):
        if TRACE in self.get_abilities():
            return self.execute_command("GET", TRACE, {})
        else:
            l.error("This device does not support the TRACE ability")
            return None

    def get_debug(self):
        if DEBUG in self.get_abilities():
            return self.execute_command("GET", DEBUG, {})
        else:
            l.error("This device does not support the DEBUG ability")
            return None