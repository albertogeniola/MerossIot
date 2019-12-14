from meross_iot.cloud.abilities import HUB_TOGGLEX
from meross_iot.logger import SUBDEVICE_LOGGER as l


class GenericSubDevice:
    id = None
    _hub = None
    online = False
    onoff = None
    last_active_time = None

    def __init__(self, subdevice_id, hub, **kwords):
        self.id = subdevice_id
        self._hub = hub
        self.update_state(kwords)

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

    def handle_push_event(self, subdevice_data, namespace):
        if namespace == HUB_TOGGLEX:
            self.onoff = subdevice_data.get('onoff')
        elif namespace is None:
            pass
        else:
            l.warn("Unsupported namespace push event: %s" % namespace)

    def update_all(self):
        pass

    def __str__(self):
        return 'ID: %s' % self.id

    # TODO
    # def __str__(self):
    #    pass
