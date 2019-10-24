from meross_iot.cloud.abilities import *
from meross_iot.cloud.device import AbstractMerossDevice
from meross_iot.logger import POWER_PLUGS_LOGGER as l
from meross_iot.meross_event import DeviceSwitchStatusEvent


class GenericHub(AbstractMerossDevice):
    # Channels
    _channels = []

    # Dictionary {channel->status}
    _state = {}
    _hub_clients = {}

    def __init__(self, cloud_client, device_uuid, **kwords):
        super(GenericHub, self).__init__(cloud_client, device_uuid, **kwords)

    def _togglex(self, id, status, channel=0, callback=None):
        payload = {'togglex': {"id": id, "onoff": status, "channel": channel}}
        return self.execute_command("SET", TOGGLEX, payload, callback=callback)

    def _handle_push_notification(self, namespace, payload, from_myself=False):
        def fire_switch_state_change(dev, channel_id, o_state, n_state, f_myself):
            if o_state != n_state:
                evt = DeviceSwitchStatusEvent(dev=dev, channel_id=channel_id, switch_state=n_state,
                                              generated_by_myself=f_myself)
                self.fire_event(evt)

        with self._state_lock:
            if namespace == HUB_TOGGLEX:
                for sensor in payload['togglex']:
                    self._update_client_data(sensor)
                # TODO: fire_switch_state_change(self, channel_index, old_switch_state, switch_state, from_myself)

            elif namespace == REPORT:
                # For now, we simply ignore push notification of these kind.
                # In the future, we might think of handling such notification by caching them
                # and avoid the network round-trip when asking for power consumption (if the latest report is
                # recent enough)
                pass

            elif namespace == HUB_MODE:
                for sensor in payload['mode']:
                    self._update_client_data(sensor)
                # TODO: fire_switch_state_change(self, channel_index, old_switch_state, switch_state, from_myself)

            # Target temperature set on the device
            elif namespace == HUB_TEMPERATURE:
                for sensor in payload['temperature']:
                    self._update_client_data(sensor)
                # TODO: fire_switch_state_change(self, channel_index, old_switch_state, switch_state, from_myself)

            else:
                l.error("Unknown/Unsupported namespace/command: %s" % namespace)

    def _update_client_data(self, client_data):
        client_id = client_data.get('id')

        # Add the sensor dictionary object
        s = self._hub_clients.get(client_id)
        if s is None:
            s = {}
            self._hub_clients[client_id] = s

        # Update the sensor data
        for k in client_data:
            if k == 'id':
                continue
            s[k] = client_data[k]

    def _get_status_impl(self):
        res = {}
        data = self.get_sys_data()['all']
        if 'digest' in data:
            for c in data['digest']['togglex']:
                res[c['channel']] = c['onoff'] == 1
        elif 'control' in data:
            res[0] = data['control']['toggle']['onoff'] == 1
        return res

    def get_status(self, client_id=0):
        with self._state_lock:
            if self._state == {}:
                self._state = self._get_status_impl()
            return self._state[client_id]

    def get_clients(self):
        return self._hub_clients.keys()

    def get_client_status(self, client_id):
        return self.get_status(client_id)

    """
    def turn_on_client(self, channel, callback=None):
        return self._channel_control_impl(c, 1, callback=callback)

    def turn_off_channel(self, channel, callback=None):
        c = self._get_channel_id(channel)
        return self._channel_control_impl(c, 0, callback=callback)

    def turn_on(self, channel=0, callback=None):
        c = self._get_channel_id(channel)
        return self._channel_control_impl(c, 1, callback=callback)

    def turn_off(self, channel=0, callback=None):
        c = self._get_channel_id(channel)
        return self._channel_control_impl(c, 0, callback=callback)
    """

    def __str__(self):
        base_str = super().__str__()
        with self._state_lock:
            if not self.online:
                return base_str
            channels = "Channels: "
            channels += ",".join(["%d = %s" % (k, "ON" if v else "OFF") for k, v in enumerate(self._state)])
            return base_str + "\n" + "\n" + channels
