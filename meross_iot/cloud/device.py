from abc import ABC, abstractmethod


class AbstractMerossDevice(ABC):
    # Device info and connection parameters
    _uuid = None
    _app_id = None
    _name = None
    _type = None
    _hwversion = None
    _fwversion = None

    # Cached list of abilities
    _abilities = None

    # Cloud client: the object that handles mqtt communication with the Meross Cloud
    _cloud_client = None

    def __init__(self, cloud_client, device_uuid, **kwords):
        self._cloud_client = cloud_client
        self._uuid = device_uuid

        if "channels" in kwords:
            self._channels = kwords['channels']

        # Informations about device
        if "devName" in kwords:
            self._name = kwords['devName']
        if "deviceType" in kwords:
            self._type = kwords['deviceType']
        if "fmwareVersion" in kwords:
            self._fwversion = kwords['fmwareVersion']
        if "hdwareVersion" in kwords:
            self._hwversion = kwords['hdwareVersion']

    def device_id(self):
        return self._uuid

    @abstractmethod
    def _handle_namespace_payload(self, namespace, message):
        """
        Handles messages coming from the device. This method should be implemented by the base class in order
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
        return self._cloud_client.execute_cmd("GET", "Appliance.System.All", {})

    def get_abilities(self):
        # TODO: Make this cached value expire after a bit...
        if self._abilities is None:
            self._abilities = self._cloud_client.execute_cmd("GET", "Appliance.System.Ability", {})['ability']
        return self._abilities

    def get_report(self):
        return self._cloud_client.execute_cmd("GET", "Appliance.System.Report", {})

