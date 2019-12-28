from meross_iot.cloud.device import AbstractMerossDevice, HUB_MTS100_ALL


class GenericSubDevice(AbstractMerossDevice):
    def __init__(self, cloud_client, subdevice_id, parent_hub, **kwords):
        super().__init__(cloud_client, parent_hub.uuid, **kwords)
        self.subdevice_id = subdevice_id
        self._hub = parent_hub
        self.name = kwords.get('subDeviceName')
        self.type = kwords.get('subDeviceType')
        self._hub.register_sub_device(self)
        self._raw_state = {}

    @property
    def last_active_time(self):
        last_active_time = self._raw_state.get('online')
        if last_active_time is None:
            self._sync_status()
            last_active_time = self._raw_state.get('online')
        return last_active_time.get('lastActiveTime')

    @property
    def online(self):
        # Subdevices do not report the online status to the HTTP API and they only talk with hubs.
        # If the hub is offline, for sure the device is offline.
        # On the other hand, if the hub is online, we cannot be 100% certain it's online.
        # In such case, we try to fetch data from the device anyways.
        if not self._hub.online:
            return False
        online = self._raw_state.get('online')
        if online is None:
            self._sync_status()
            online = self._raw_state.get('online')
        return online.get('status', 0) == 1

    def _sync_status(self):
        payload = {'all': [{'id': self.subdevice_id}]}
        res = self._hub.execute_command('GET', HUB_MTS100_ALL, payload)
        data = res.get('all')
        for device_data in data:
            if device_data.get('id') == self.subdevice_id:
                self._raw_state.update(device_data)
        return self._raw_state

    def get_status(self):
        if self._raw_state == {}:
            return self._sync_status()
        else:
            return self._raw_state

    def _handle_push_notification(self, namespace, payload, from_myself=False):
        # TODO: log
        pass

    def __str__(self):
        return "{}".format(self._raw_state)
