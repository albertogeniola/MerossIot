from meross_iot.cloud.abilities import HUB_BATTERY
from meross_iot.cloud.device import AbstractMerossDevice, HUB_ONLINE
from meross_iot.cloud.timeouts import LONG_TIMEOUT
from meross_iot.logger import SUBDEVICE_LOGGER as l
from meross_iot.meross_event import DeviceOnlineStatusEvent


class GenericSubDevice(AbstractMerossDevice):
    def __init__(self, cloud_client, subdevice_id, parent_hub, **kwords):
        super().__init__(cloud_client, parent_hub.uuid, **kwords)
        self.subdevice_id = subdevice_id
        self._hub = parent_hub
        self.name = kwords.get('subDeviceName')
        self.type = kwords.get('subDeviceType')
        self._hub.register_sub_device(self)
        self._raw_state = {}

    def _get_property(self, parent, child, trigger_update_if_unavailable=True):
        prop = self._raw_state.get(parent, {}).get(child)
        if prop is None and trigger_update_if_unavailable and self.online:
            self._sync_status()
            prop = self._raw_state.get(parent, {}).get(child)
        return prop

    def get_battery_status(self):
        payload = {'battery': [{'id': self.subdevice_id}]}
        data = self.execute_command('GET', HUB_BATTERY, payload).get('battery')[0]
        return data.get('value')

    @property
    def last_active_time(self):
        return self._get_property('online', 'lastActiveTime', trigger_update_if_unavailable=False)

    @property
    def online(self):
        # In any case, if the hub is offline, for sure the device is offline.
        if not self._hub.online:
            return False

        # Subdevices do not report the online status to the HTTP API and they only talk with hubs.
        # So, the idea is to rely to the last_active_time - if available, assuming any interaction < 1 minute ago
        # means the device is still online. If the last_active_time is older, then we try to "ping" the subdevice.
        last_active_on = self.last_active_time
        if last_active_on is None:
            self._sync_status()
        online = self._raw_state.get('online', {}).get('status', 0)
        return online == 1

    @online.setter
    def online(self, online):
        pass

    def _sync_status(self, timeout=LONG_TIMEOUT):
        payload = {'all': [{'id': self.subdevice_id}]}
        status_token = self._status_token
        if status_token is not None:
            res = self._hub.execute_command('GET', status_token, payload)
            data = res.get('all')
            if (data is not None):
                for device_data in data:
                    if device_data.get('id') == self.subdevice_id:
                        self._raw_state.update(device_data)
        return self._raw_state

    @property
    def _status_token(self):
        l.error("GenericSubDevice._status_token should be overwritten by subclass")

    def get_status(self, force_status_refresh=False, timeout=LONG_TIMEOUT):
        if self._raw_state == {} or force_status_refresh:
            return self._sync_status(timeout=timeout)
        else:
            return self._raw_state

    def _handle_push_notification(self, namespace, payload, from_myself=False):
        # The only "common" push notification for all sub-devices seems to be the HUB_ONLINE.
        # We handle this one only for generic sub devices.
        if namespace == HUB_ONLINE:
            online = self._raw_state.get('online')
            if online is None:
                online = {}
                self._raw_state['online'] = online
            online.update(payload)
            online_status = online.get('status')==1
            evt = DeviceOnlineStatusEvent(dev=self, current_status=online_status)
            self.fire_event(evt)
            return True

    def __str__(self):
        return "{}".format(self._raw_state)
