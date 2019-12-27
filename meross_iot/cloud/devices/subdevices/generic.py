from meross_iot.cloud.device import AbstractMerossDevice, HUB_MTS100_ALL
from meross_iot.cloud.timeouts import SHORT_TIMEOUT


class GenericSubDevice(AbstractMerossDevice):
    def __init__(self, cloud_client, subdevice_id, parent_hub, **kwords):
        super().__init__(cloud_client, parent_hub.uuid, **kwords)
        self.subdevice_id = subdevice_id
        self._hub = parent_hub
        self.name = kwords.get('subDeviceName')
        self.type = kwords.get('subDeviceType')
        self._hub.register_sub_device(self)
        self._state = {}

    def notify_hub_state_change(self, subdevice_data):
        # Update the sensor data
        for k, v in subdevice_data.items():
            if k == 'id':
                continue
            elif k == 'status':
                self.online = v == 1
            elif k == 'onoff':
                self.onoff = v
            elif k == 'lastActiveTime':
                self.last_active_time = v
            else:
                # TODO: log the anomaly
                pass

    def _sync_status(self):
        payload = {'all': [{'id': self.subdevice_id}]}
        res = self._hub.execute_command('GET', HUB_MTS100_ALL, payload)
        data = res.get('all')
        for device_data in data:
            if device_data.get('id') == self.subdevice_id:
                self._raw_state.update(device_data)

    def get_status(self):
        if self._raw_state == {}:
            self._sync_status()
        else:
            return self._raw_state

    def _handle_push_notification(self, namespace, payload, from_myself=False):
        # TODO: log
        pass

    def __str__(self):
        return "{}".format(self._raw_state)
