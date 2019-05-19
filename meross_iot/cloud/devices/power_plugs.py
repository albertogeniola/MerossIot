from meross_iot.cloud.abilities import *
from meross_iot.cloud.device import AbstractMerossDevice
from meross_iot.logger import POWER_PLUGS_LOGGER as l
from meross_iot.meross_event import DeviceSwitchStatusEvent


class GenericPlug(AbstractMerossDevice):
    # Channels
    _channels = []

    # Dictionary {channel->status}
    _state = {}

    def __init__(self, cloud_client, device_uuid, **kwords):
        super(GenericPlug, self).__init__(cloud_client, device_uuid, **kwords)

    def _get_consumptionx(self):
        return self.execute_command("GET", CONSUMPTIONX, {})

    def _get_electricity(self):
        return self.execute_command("GET", ELECTRICITY, {})

    def _toggle(self, status, callback=None):
        payload = {"channel": 0, "toggle": {"onoff": status}}
        return self.execute_command("SET", TOGGLE, payload, callback=callback)

    def _togglex(self, channel, status, callback=None):
        payload = {'togglex': {"onoff": status, "channel": channel}}
        return self.execute_command("SET", TOGGLEX, payload, callback=callback)

    def _channel_control_impl(self, channel, status, callback=None):
        if TOGGLE in self.get_abilities():
            return self._toggle(status, callback=callback)
        elif TOGGLEX in self.get_abilities():
            return self._togglex(channel, status, callback=callback)
        else:
            raise Exception("The current device does not support neither TOGGLE nor TOGGLEX.")

    def _handle_push_notification(self, namespace, payload, from_myself=False):
        def fire_switch_state_change(dev, channel_id, o_state, n_state, f_myself):
            if o_state != n_state:
                evt = DeviceSwitchStatusEvent(dev=dev, channel_id=channel_id, switch_state=n_state,
                                              generated_by_myself=f_myself)
                self.fire_event(evt)

        with self._state_lock:
            if namespace == TOGGLE:
                # Update the local state and fire the event only if the state actually changed
                channel_index = 0
                old_switch_state = self._state.get(channel_index)
                switch_state = payload['toggle']['onoff'] == 1
                self._state[channel_index] = switch_state
                fire_switch_state_change(self, channel_index, old_switch_state, switch_state, from_myself)

            elif namespace == TOGGLEX:
                if isinstance(payload['togglex'], list):
                    for c in payload['togglex']:
                        # Update the local state and fire the event only if the state actually changed
                        channel_index = c['channel']
                        old_switch_state = self._state.get(channel_index)
                        switch_state = c['onoff'] == 1
                        self._state[channel_index] = switch_state
                        fire_switch_state_change(self, channel_index, old_switch_state, switch_state, from_myself)

                elif isinstance(payload['togglex'], dict):
                    # Update the local state and fire the event only if the state actually changed
                    channel_index = payload['togglex']['channel']
                    old_switch_state = self._state.get(channel_index)
                    switch_state = payload['togglex']['onoff'] == 1
                    self._state[channel_index] = switch_state
                    fire_switch_state_change(self, channel_index, old_switch_state, switch_state, from_myself)

            elif namespace == REPORT or namespace == CONSUMPTIONX:
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
            if self._state == {}:
                self._state = self._get_status_impl()
            return self._state[c]

    def get_power_consumption(self):
        if CONSUMPTIONX in self.get_abilities():
            return self._get_consumptionx()['consumptionx']
        else:
            # Not supported!
            return None

    def get_electricity(self):
        if ELECTRICITY in self.get_abilities():
            return self._get_electricity()['electricity']
        else:
            # Not supported!
            return None

    def get_channels(self):
        return self._channels

    def get_channel_status(self, channel):
        c = self._get_channel_id(channel)
        return self.get_status(c)

    def turn_on_channel(self, channel, callback=None):
        c = self._get_channel_id(channel)
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

    def get_usb_channel_index(self):
        # Look for the usb channel
        for i, c in enumerate(self.get_channels()):
            if 'type' in c and c['type'] == 'USB':
                return i
        return None

    def enable_usb(self, callback=None):
        c = self.get_usb_channel_index()
        if c is None:
            return
        else:
            return self.turn_on_channel(c, callback=callback)

    def disable_usb(self, callback=None):
        c = self.get_usb_channel_index()
        if c is None:
            return
        else:
            return self.turn_off_channel(c, callback=callback)

    def get_usb_status(self):
        c = self.get_usb_channel_index()
        if c is None:
            return
        else:
            return self.get_channel_status(c)

    def __str__(self):
        base_str = super().__str__()
        with self._state_lock:
            if not self.online:
                return base_str
            channels = "Channels: "
            channels += ",".join(["%d = %s" % (k, "ON" if v else "OFF") for k, v in enumerate(self._state)])
            return base_str + "\n" + "\n" + channels
