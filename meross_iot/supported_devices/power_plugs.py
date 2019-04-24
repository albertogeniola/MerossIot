from threading import RLock

from meross_iot.supported_devices.abilities import *
from meross_iot.supported_devices.timeouts import SHORT_TIMEOUT, LONG_TIMEOUT
from meross_iot.supported_devices.protocol import AbstractMerossDevice, l


class GenericPlug(AbstractMerossDevice):
    _state_lock = None

    # Channels
    _channels = []

    # Dictionary {channel->status}
    _state = None

    def __init__(self, token, key, user_id, **kwords):
        self._state_lock = RLock()
        super(GenericPlug, self).__init__(token, key, user_id, **kwords)

    def _get_consumptionx(self):
        return self._execute_cmd("GET", CONSUMPTIONX, {})

    def _get_electricity(self):
        return self._execute_cmd("GET", ELECTRICITY, {})

    def _toggle(self, status):
        payload = {"channel": 0, "toggle": {"onoff": status}}
        return self._execute_cmd("SET", TOGGLE, payload)

    def _togglex(self, channel, status):
        payload = {'togglex': {"onoff": status, "channel": channel}}
        return self._execute_cmd("SET", TOGGLEX, payload)

    def _channel_control_impl(self, channel, status):
        if TOGGLE in self.get_abilities():
            return self._toggle(status)
        elif TOGGLEX in self.get_abilities():
            return self._togglex(channel, status)
        else:
            raise Exception("The current device does not support neither TOGGLE nor TOGGLEX.")

    def _handle_namespace_payload(self, namespace, payload):
        with self._state_lock:
            if namespace == TOGGLE:
                self._state[0] = payload['toggle']['onoff'] == 1
            elif namespace == TOGGLEX:
                if isinstance(payload['togglex'], list):
                    for c in payload['togglex']:
                        channel_index = c['channel']
                        self._state[channel_index] = c['onoff'] == 1
                elif isinstance(payload['togglex'], dict):
                    channel_index = payload['togglex']['channel']
                    self._state[channel_index] = payload['togglex']['onoff'] == 1
            else:
                l.error("Unknown/Unsupported namespace/command: %s" % namespace)

    def _get_status_impl(self):
        res = {}
        data = self.get_sys_data()['all']
        if 'digest' in data:
            for c in data['digest']['togglex']:
                res[c['channel']] = c['onoff'] == 1
        elif 'control' in data:
            res[0] = data['control']['toggle']['onoff'] == 1
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
        # On the contrary, we only call it the first time. Then, the rest of the API will silently listen
        # for state changes and will automatically update the self._state structure listening for
        # messages of the device.
        # Such approach, however, has a side effect. If we call TOGGLE/TOGGLEX and immediately after we call
        # get_status(), the reported status will be still the old one. This is a race condition because the
        # "status" RESPONSE will be delivered some time after the TOGGLE REQUEST. It's not a big issue for now,
        # and synchronizing the two things would be inefficient and probably not very useful.
        # Just remember to wait some time before testing the status of the item after a toggle.
        with self._state_lock:
            c = self._get_channel_id(channel)
            if self._state is None:
                self._state = self._get_status_impl()
            return self._state[c]

    def supports_consumption_reading(self):
        return CONSUMPTIONX in self.get_abilities()

    def supports_electricity_reading(self):
        return ELECTRICITY in self.get_abilities()

    def get_power_consumption(self):
        if CONSUMPTIONX in self.get_abilities():
            return self._get_consumptionx()
        else:
            # Not supported!
            return None

    def get_electricity(self):
        if ELECTRICITY in self.get_abilities():
            return self._get_electricity()
        else:
            # Not supported!
            return None

    def get_channels(self):
        return self._channels

    def get_wifi_list(self):
        return self._execute_cmd("GET", WIFI_LIST, {}, timeout=LONG_TIMEOUT)

    def get_trace(self):
        return self._execute_cmd("GET", "Appliance.Config.Trace", {})

    def get_debug(self):
        return self._execute_cmd("GET", "Appliance.System.Debug", {})

    def get_channel_status(self, channel):
        c = self._get_channel_id(channel)
        return self.get_status(c)

    def turn_on_channel(self, channel):
        c = self._get_channel_id(channel)
        return self._channel_control_impl(c, 1)

    def turn_off_channel(self, channel):
        c = self._get_channel_id(channel)
        return self._channel_control_impl(c, 0)

    def turn_on(self, channel=0):
        c = self._get_channel_id(channel)
        return self._channel_control_impl(c, 1)

    def turn_off(self, channel=0):
        c = self._get_channel_id(channel)
        return self._channel_control_impl(c, 0)

    def get_usb_channel_index(self):
        # Look for the usb channel
        for i, c in enumerate(self.get_channels()):
            if 'type' in c and c['type'] == 'USB':
                return i
        return None

    def enable_usb(self):
        c = self.get_usb_channel_index()
        if c is None:
            return
        else:
            return self.turn_on_channel(c)

    def disable_usb(self):
        c = self.get_usb_channel_index()
        if c is None:
            return
        else:
            return self.turn_off_channel(c)

    def get_usb_status(self):
        c = self.get_usb_channel_index()
        if c is None:
            return
        else:
            return self.get_channel_status(c)

    def __str__(self):
        basic_info = "%s (%s, %d channels, HW %s, FW %s): " % (
            self._name,
            self._type,
            len(self._channels),
            self._hwversion,
            self._fwversion
        )

        for i, c in enumerate(self._channels):
            channel_type = c['type'] if 'type' in c else "Master" if c == {} else "Unknown"
            channel_state = "On" if self.get_status(i) else "Off"
            channel_desc = "%s=%s" % (channel_type, channel_state)
            basic_info += channel_desc + ", "

        return basic_info