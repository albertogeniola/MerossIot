from meross_iot.cloud.abilities import *
from meross_iot.cloud.device import AbstractMerossDevice
from meross_iot.logger import POWER_PLUGS_LOGGER as l
from meross_iot.meross_event import DeviceHubStatusEvent


class GenericHub(AbstractMerossDevice):
    # Handles the state of this specific HUB
    _state = {}
    _hub_state = {}

    def __init__(self, cloud_client, device_uuid, **kwords):
        super(GenericHub, self).__init__(cloud_client, device_uuid, **kwords)

    def _togglex(self, subdevice_id, status, channel=0, callback=None):
        payload = {'togglex': {"id": subdevice_id, "onoff": status, "channel": channel}}
        return self.execute_command("SET", TOGGLEX, payload, callback=callback)

    def _handle_push_notification(self, namespace, payload, from_myself=False):
        def fire_hub_state_change(dev, subdevice_id, state_data, f_myself):
            evt = DeviceHubStatusEvent(hubdevice=dev, subdevice_id=subdevice_id, state=state_data,
                                          generated_by_myself=f_myself)
            self.fire_event(evt)

        with self._state_lock:
            if namespace == HUB_TOGGLEX:
                for sensor in payload['togglex']:
                    self._update_client_data(sensor)
                    fire_hub_state_change(self, sensor.get('id'), sensor, from_myself)

            elif namespace == REPORT:
                # For now, we simply ignore push notification of these kind.
                # In the future, we might think of handling such notification by caching them
                # and avoid the network round-trip when asking for power consumption (if the latest report is
                # recent enough)
                pass

            elif namespace == HUB_MODE:
                for sensor in payload['mode']:
                    self._update_client_data(sensor)
                    fire_hub_state_change(self, sensor.get('id'), sensor, from_myself)

            # Target temperature set on the device
            elif namespace == HUB_TEMPERATURE:
                for sensor in payload['temperature']:
                    self._update_client_data(sensor)
                    fire_hub_state_change(self, sensor.get('id'), sensor, from_myself)

            else:
                l.error("Unknown/Unsupported namespace/command: %s" % namespace)

    def _update_client_data(self, client_data):
        client_id = client_data.get('id')

        # Add the sensor dictionary object
        s = self._hub_state.get(client_id)
        if s is None:
            s = {}
            self._hub_state[client_id] = s

        # Update the sensor data
        for k in client_data:
            if k == 'id':
                continue
            s[k] = client_data[k]

    def _get_status_impl(self):
        res = {}
        data = self.get_sys_data()['all']
        hub_data = data.get('digest').get('hub')
        res['hub_id'] = hub_data.get('hubId')
        res['mode'] = hub_data.get('mode')
        for subdevice in hub_data.get('subdevice'):
            self._update_client_data(subdevice)
        return res

    def get_status(self):
        with self._state_lock:
            if self._state == {}:
                self._state = self._get_status_impl()
            self._state['subdevices'] = self._hub_state
            return self._state

    def get_subdevice_state(self, subdevice_id):
        return self._state['subdevices'].get(subdevice_id)

    def get_subdevices(self):
        return self._state['subdevices'].keys()

    def turn_on_subdevice(self, subdevice_id, channel=0, callback=None):
        return self._togglex(subdevice_id, 1, channel, callback=callback)

    def turn_off_subdevice(self, subdevice_id, channel=0, callback=None):
        return self._togglex(subdevice_id, 1, channel, callback=callback)

    def __str__(self):
        base_str = super().__str__()
        with self._state_lock:
            if not self.online:
                return base_str
            # TODO: fix this method. We'd probably want to print some more meaningful info
            return base_str
