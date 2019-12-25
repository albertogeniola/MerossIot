from meross_iot.cloud.device import AbstractMerossDevice
from meross_iot.cloud.timeouts import SHORT_TIMEOUT


class GenericSubDevice(AbstractMerossDevice):
    subdevice_id = None
    _hub = None
    onoff = None
    last_active_time = None

    def __init__(self, cloud_client, subdevice_id, parent_hub, **kwords):
        super().__init__(cloud_client, parent_hub.uuid, **kwords)
        self.subdevice_id = subdevice_id
        self._hub = parent_hub
        self.name = kwords.get('subDeviceName')
        self.type = kwords.get('subDeviceType')
        self._hub.register_sub_device(self)

    def update_state(self, subdevice_data):
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

    def _handle_push_notification(self, namespace, payload, from_myself=False):
        pass

    def get_status(self):
        pass

    # TODO
    # def __str__(self):
    #    pass
