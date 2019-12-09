from meross_iot.cloud.abilities import *
from meross_iot.cloud.device import AbstractMerossDevice
from meross_iot.logger import POWER_PLUGS_LOGGER as l
from meross_iot.meross_event import DeviceHubStatusEvent


class GenericHub(AbstractMerossDevice):
    # Handles the state of this specific HUB
    _state = {}
    _sub_devices = {}

    def __init__(self, cloud_client, device_uuid, **kwords):
        super(GenericHub, self).__init__(cloud_client, device_uuid, **kwords)

    def _update_subdevice_data(self, client_data):
        client_id = client_data.get('id')

        # Check if the sensor is already present into the list of subdevices
        subdev = self._sub_devices.get(client_id)
        if subdev is None:
            subdev = HubSubDevice(subdevice_id=client_id, hub=self, **client_data)
            self._sub_devices[client_id] = subdev

        subdev.update_state(client_data)

    def _get_status_impl(self):
        res = {}
        data = self.get_sys_data()['all']
        hub_data = data.get('digest').get('hub')
        res['hub_id'] = hub_data.get('hubId')
        res['mode'] = hub_data.get('mode')
        for subdevice in hub_data.get('subdevice'):
            self._update_subdevice_data(subdevice)
        return res

    def get_status(self):
        with self._state_lock:
            if self._state == {}:
                self._state = self._get_status_impl()
            return self._state

    def _handle_push_notification(self, namespace, payload, from_myself=False):
        def fire_hub_state_change(dev, subdevice_id, state_data, f_myself):
            evt = DeviceHubStatusEvent(hubdevice=dev, subdevice_id=subdevice_id, state=state_data,
                                       generated_by_myself=f_myself)
            self.fire_event(evt)

        def update_and_fire_event(sensor):
            subdevice_id = sensor.get('id')
            self._update_subdevice_data(sensor)
            fire_hub_state_change(self, subdevice_id, self.get_subdevice_state(subdevice_id), from_myself)

        with self._state_lock:
            if namespace == HUB_TOGGLEX:
                for sensor in payload['togglex']:
                    update_and_fire_event(sensor)

            elif namespace == REPORT:
                pass

            elif namespace == HUB_MODE:
                for sensor in payload['mode']:
                    update_and_fire_event(sensor)

            # Target temperature set on the device
            elif namespace == HUB_TEMPERATURE:
                for sensor in payload['temperature']:
                    update_and_fire_event(sensor)

            else:
                l.error("Unknown/Unsupported namespace/command: %s" % namespace)

    def _togglex(self, subdevice_id, status, channel=0, callback=None):
        payload = {'togglex': [{"id": subdevice_id, "onoff": status, "channel": channel}]}
        return self.execute_command("SET", HUB_TOGGLEX, payload, callback=callback)

    def get_subdevice_state(self, subdevice_id):
        return self._sub_devices.get(subdevice_id)

    def get_subdevices(self):
        return self._sub_devices.keys()

    def turn_on_subdevice(self, subdevice_id, channel=0, callback=None):
        return self._togglex(subdevice_id, 1, channel, callback=callback)

    def turn_off_subdevice(self, subdevice_id, channel=0, callback=None):
        return self._togglex(subdevice_id, 0, channel, callback=callback)

    def __str__(self):
        base_str = super().__str__()
        with self._state_lock:
            if not self.online:
                return base_str
            # TODO: fix this method. We'd probably want to print some more meaningful info
            return base_str


class HubSubDevice:
    id = None
    _hub = None
    online = False
    last_active_time = None

    def __init__(self, subdevice_id, hub, **kwords):
        self.id = subdevice_id
        self._hub = hub
        self.online = kwords.get('status')
        self.onoff = kwords.get('onoff')
        self.last_active_time = kwords.get('lastActiveTime')

    def update_state(self, client_data):
        # Update the sensor data
        for k, v in client_data.items():
            if k == 'id':
                continue
            elif k == 'status':
                self.online = v
            elif k == 'onoff':
                self.onoff = v
            elif k == 'lastActiveTime':
                self.last_active_time = v
            else:
                setattr(self, k, v)

    # TODO
    #def __str__(self):
    #    pass