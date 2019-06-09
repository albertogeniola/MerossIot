from meross_iot.cloud.abilities import *
from meross_iot.cloud.device import AbstractMerossDevice
from meross_iot.logger import BULBS_LOGGER as l
from meross_iot.meross_event import BulbSwitchStateChangeEvent, BulbLightStateChangeEvent


def to_rgb(rgb):
    if rgb is None:
        return None
    elif isinstance(rgb, int):
        return rgb
    elif isinstance(rgb, tuple):
        red, green, blue = rgb
    elif isinstance(rgb, dict):
        red = rgb['red']
        green = rgb['green']
        blue = rgb['blue']
    else:
        raise Exception("Invalid value for RGB!")

    r = red << 16
    g = green << 8
    b = blue

    return r+g+b


class GenericBulb(AbstractMerossDevice):
    # Bulb state: dictionary of channel-id/bulb-state
    _state = None

    def __init__(self, cloud_client, device_uuid, **kwords):
        self._state = {}
        super(GenericBulb, self).__init__(cloud_client, device_uuid, **kwords)

    def _channel_control_impl(self, channel, status):
        if TOGGLE in self.get_abilities():
            return self._toggle(status)
        elif TOGGLEX in self.get_abilities():
            return self._togglex(channel, status)
        else:
            raise Exception("The current device does not support neither TOGGLE nor TOGGLEX.")

    def _update_state(self, channel, **kwargs):
        with self._state_lock:
            if channel not in self._state:
                self._state[channel] = {}
            for k in kwargs:
                if k == 'onoff':
                    self._state[channel]['onoff'] = kwargs[k]
                elif kwargs[k] is not None:
                    self._state[channel][k] = kwargs[k]

    def _toggle(self, status):
        payload = {"channel": 0, "toggle": {"onoff": status}}
        return self.execute_command("SET", TOGGLE, payload)

    def _togglex(self, channel, status):
        payload = {'togglex': {"onoff": status, "channel": channel}}
        return self.execute_command("SET", TOGGLEX, payload)

    def _handle_push_notification(self, namespace, payload, from_myself=False):
        def fire_bulb_switch_state_change(dev, channel_id, o_state, n_state, f_myself):
            if o_state != n_state:
                evt = BulbSwitchStateChangeEvent(dev=dev, channel_id=channel_id, is_on=n_state,
                                                 generated_by_myself=f_myself)
                self.fire_event(evt)

        def fire_bulb_light_state_change(dev, channel_id, o_state, n_state, f_myself):
            if o_state != n_state:
                evt = BulbLightStateChangeEvent(dev=dev, channel_id=channel_id, light_state=n_state,
                                                generated_by_myself=f_myself)
                self.fire_event(evt)

        with self._state_lock:
            if namespace == TOGGLE:
                on_status=payload['toggle']['onoff'] == 1
                channel_index = 0
                old_state = self._state.get(channel_index)
                new_state = on_status
                self._update_state(channel=0, onoff=on_status)
                fire_bulb_switch_state_change(self, channel_id=0, o_state=old_state, n_state=new_state,
                                              f_myself=from_myself)

            elif namespace == TOGGLEX:
                if isinstance(payload['togglex'], list):
                    for c in payload['togglex']:
                        channel_index = c['channel']
                        on_status = c['onoff'] == 1
                        old_state = self._state.get(channel_index)
                        if old_state is not None:
                            old_state = old_state.get('onoff')
                        self._update_state(channel=channel_index, onoff=on_status)
                        fire_bulb_switch_state_change(self, channel_id=channel_index, o_state=old_state,
                                                      n_state=on_status, f_myself=from_myself)
                elif isinstance(payload['togglex'], dict):
                    channel_index = payload['togglex']['channel']
                    on_status = payload['togglex']['onoff'] == 1
                    old_state = self._state.get(channel_index).get('onoff')
                    if old_state is not None:
                        old_state = old_state.get('onoff')
                    self._update_state(channel=channel_index, onoff=on_status)
                    fire_bulb_switch_state_change(self, channel_id=channel_index, o_state=old_state, n_state=on_status,
                                                  f_myself=from_myself)

            elif namespace == LIGHT:
                channel_index = payload['light']['channel']
                old_state = self._state.get(channel_index)
                new_state = payload['light']
                del new_state['channel']
                self._update_state(channel=channel_index, **new_state)
                fire_bulb_light_state_change(self, channel_id=channel_index, o_state=old_state, n_state=new_state,
                                             f_myself=from_myself)

            elif namespace == REPORT:
                # For now, we simply ignore push notification of these kind.
                # In the future, we might think of handling such notification by caching them
                # and avoid the network round-trip when asking for power consumption (if the latest report is
                # recent enough)
                pass

            else:
                l.error("Unknown/Unsupported namespace/command: %s" % namespace)

    def _get_status_impl(self):
        res = {}
        data = self.get_sys_data()['all']
        if 'digest' in data:
            light_channel = data['digest']['light']['channel']
            res[light_channel] = data['digest']['light']

            for c in data['digest']['togglex']:
                res[c['channel']]['onoff'] = c['onoff'] == 1
        elif 'control' in data:
            res[0]['onoff'] = data['control']['toggle']['onoff'] == 1
        return res

    def _get_channel_id(self, channel):
        # Otherwise, if the passed channel looks like the channel spec, lookup its array indexindex
        if channel in self._channels:
            return self._channels.index(channel)

        # if a channel name is given, lookup the channel id from the name
        if isinstance(channel, str):
            for i, c in enumerate(self.get_channels()):
                if c['devName'] == channel:
                    return c['channel']

        # If an integer is given assume that is the channel ID
        elif isinstance(channel, int):
            return channel

        # In other cases return an error
        raise Exception("Invalid channel specified.")

    def get_status(self, channel=0):
        # In order to optimize the network traffic, we don't call the get_status() api at every request.
        # On the contrary, we call it the first time. Then, the rest of the API will silently listen
        # for state changes and will automatically update the self._state structure listening for
        # messages of the device.
        # Such approach, however, has a side effect. If we call TOGGLE/TOGGLEX and immediately after we call
        # get_status(), the reported status will be still the old one. This is a race condition because the
        # "status" RESPONSE will be delivered some time after the TOGGLE REQUEST. It's not a big issue for now,
        # and synchronizing the two things would be inefficient and probably not very useful.
        # Just remember to wait some time before testing the status of the item after a toggle.
        c = self._get_channel_id(channel)
        if self._state == {}:
            current_state = self._get_status_impl()
            with self._state_lock:
                self._state = current_state
        return self._state[c]

    def get_channels(self):
        return self._channels

    def get_channel_status(self, channel):
        ch_id = self._get_channel_id(channel)
        c = self._get_channel_id(ch_id)
        return self.get_status(c)

    def turn_on_channel(self, channel):
        ch_id = self._get_channel_id(channel)
        c = self._get_channel_id(ch_id)
        return self._channel_control_impl(c, 1)

    def turn_off_channel(self, channel):
        ch_id = self._get_channel_id(channel)
        c = self._get_channel_id(ch_id)
        return self._channel_control_impl(c, 0)

    def turn_on(self, channel=0):
        ch_id = self._get_channel_id(channel)
        c = self._get_channel_id(ch_id)
        return self._channel_control_impl(c, 1)

    def turn_off(self, channel=0):
        ch_id = self._get_channel_id(channel)
        c = self._get_channel_id(ch_id)
        return self._channel_control_impl(c, 0)

    def set_light_color(self, channel=0, rgb=None, luminance=100, temperature=100, capacity=5):
        ch_id = self._get_channel_id(channel)

        # Convert the RGB to integer
        color = to_rgb(rgb)

        payload = {
            'light': {
                'capacity': capacity,
                'channel': ch_id,
                'gradual': 0,
                'luminance': luminance,
                'rgb': color,
                'temperature': temperature
            }
        }

        # TODO: fix this as soon as we get hands on a real MSS560 and see what the payload looks like...
        # handle mss560m differently
        if self.type.lower() == 'mss560m':
            pl = {
                'light': self.get_light_color()
            }
            pl['light']['channel'] = channel
            pl['light']['luminance'] = luminance
            payload = pl

        self.execute_command(command='SET', namespace=LIGHT, payload=payload)

    def get_light_color(self, channel=0):
        ch_id = self._get_channel_id(channel)
        return self.get_status(channel=ch_id)

    def get_power_consumption(self):
        return None

    def get_electricity(self):
        return None

    def __str__(self):
        base_str = super().__str__()
        with self._state_lock:
            if not self.online:
                return base_str
            channels = "Channels: "
            channels += ",".join(["%d = %s" % (k, "ON" if v else "OFF") for k, v in enumerate(self._state)])
            return base_str + "\n" + "\n" + channels
