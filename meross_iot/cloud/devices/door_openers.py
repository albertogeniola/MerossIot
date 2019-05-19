from meross_iot.cloud.abilities import *
from meross_iot.cloud.device import AbstractMerossDevice
from meross_iot.logger import POWER_PLUGS_LOGGER as l
from meross_iot.meross_event import DeviceSwitchStatusEvent, DeviceDoorStatusEvent


class GenericGarageDoorOpener(AbstractMerossDevice):
    # Channels
    _channels = []

    # Dictionary {channel_id (door) -> status}
    _door_state = {}

    # Dictionary {channel_id -> status}
    _switch_state = {}

    def __init__(self, cloud_client, device_uuid, **kwords):
        super(GenericGarageDoorOpener, self).__init__(cloud_client, device_uuid, **kwords)

    def _togglex(self, channel, status, callback=None):
        payload = {'togglex': {"onoff": status, "channel": channel}}
        return self.execute_command("SET", TOGGLEX, payload, callback=callback)

    def get_status(self):
        return {'switches': self._switch_state, 'doors': self._door_state}

    def _handle_push_notification(self, namespace, payload, from_myself=False):
        def fire_switch_state_change(dev, channel_id, o_state, n_state, f_myself):
            if o_state != n_state:
                evt = DeviceSwitchStatusEvent(dev=dev, channel_id=channel_id, switch_state=n_state,
                                              generated_by_myself=f_myself)
                self.fire_event(evt)

        def fire_garage_door_state_change(dev, channel_id, o_state, n_state, f_myself):
            if o_state != n_state:
                evt = DeviceDoorStatusEvent(dev=dev, channel_id=channel_id, door_state=n_state,
                                            generated_by_myself=f_myself)
                self.fire_event(evt)

        with self._state_lock:
            if namespace == TOGGLEX:
                if isinstance(payload['togglex'], list):
                    for c in payload['togglex']:
                        # Update the local state and fire the event only if the state actually changed
                        channel_index = c['channel']
                        old_switch_state = self._switch_state.get(channel_index)
                        switch_state = c['onoff'] == 1
                        self._switch_state[channel_index] = switch_state
                        fire_switch_state_change(self, channel_index, old_switch_state, switch_state, from_myself)

                elif isinstance(payload['togglex'], dict):
                    # Update the local state and fire the event only if the state actually changed
                    channel_index = payload['togglex']['channel']
                    old_switch_state = self._switch_state.get(channel_index)
                    switch_state = payload['togglex']['onoff'] == 1
                    self._switch_state[channel_index] = switch_state
                    fire_switch_state_change(self, channel_index, old_switch_state, switch_state, from_myself)
            elif namespace == GARAGE_DOOR_STATE:
                for door in payload['state']:
                    channel_index = door['channel']
                    state = door['open'] == 1
                    old_state = self._door_state[channel_index]
                    fire_garage_door_state_change(self, channel_index, old_state, state, from_myself)
            else:
                l.error("Unknown/Unsupported namespace/command: %s" % namespace)

    def _get_status_impl(self):
        switches = {}
        garage = {}
        data = self.get_sys_data()['all']
        if 'digest' in data:
            for c in data['digest']['togglex']:
                switches[c['channel']] = c['onoff'] == 1
            for c in data['digest']['garageDoor']:
                garage[c['channel']] = c['open'] == 1
        return switches, garage

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

    def get_switch_status(self, channel=0):
        with self._state_lock:
            c = self._get_channel_id(channel)
            if self._switch_state == {}:
                self._switch_state, self._door_state = self._get_status_impl()
            return self._switch_state[c]

    def get_door_status(self, channel=0):
        with self._state_lock:
            c = self._get_channel_id(channel)
            if self._door_state == {}:
                self._switch_state, self._door_state = self._get_status_impl()
            return self._door_state[c]

    def get_channel_status(self, channel=0):
        with self._state_lock:
            c = self._get_channel_id(channel)
            if self._switch_state == {}:
                self._switch_state, self._door_state = self._get_status_impl()
            return self._switch_state[c]

    def open_door(self, channel=0, callback=None):
        c = self._get_channel_id(channel)
        return self._togglex(c, 1, callback=callback)

    def close_door(self, channel=0, callback=None):
        c = self._get_channel_id(channel)
        return self._togglex(c, 0, callback=callback)

    def get_channels(self):
        return self._channels

    def __str__(self):
        base_str = super().__str__()
        with self._state_lock:
            if not self.online:
                return base_str
            doors = "Doors: "
            doors += ",".join(["%d = %s" % (k, "OPEN" if v else "CLOSED") for k, v in enumerate(self._door_state)])
            channels = "Channels: "
            channels += ",".join(["%d = %s" % (k, "ON" if v else "OFF") for k, v in enumerate(self._switch_state)])
            return base_str + "\n" + doors + "\n" + channels
