from meross_iot.cloud.abilities import *
from meross_iot.cloud.device import AbstractMerossDevice
from meross_iot.logger import POWER_PLUGS_LOGGER as l
from meross_iot.meross_event import DeviceHubStatusEvent
from meross_iot.cloud.devices.subdevices.generic import GenericSubDevice
from meross_iot.cloud.devices.subdevices.thermostats import ValveSubDevice


def get_sub_device(subdevice_id, hub, **client_data):
    if 'mts100v3' in client_data or 'mts100' in client_data:
        return ValveSubDevice(subdevice_id=subdevice_id, hub=hub, **client_data)
    else:
        # TODO: log unknown subdevice
        return GenericSubDevice(subdevice_id=subdevice_id, hub=hub, **client_data)


class GenericHub(AbstractMerossDevice):
    # Handles the state of this specific HUB
    _state = {}
    _sub_devices = {}

    def __init__(self, cloud_client, device_uuid, **kwords):
        super(GenericHub, self).__init__(cloud_client, device_uuid, **kwords)

    def _update_subdevice_data(self, client_data, namespace):
        client_id = client_data.get('id')

        # Check if the sensor is already present into the list of subdevices
        subdev = self._sub_devices.get(client_id)
        if subdev is None:
            subdev = get_sub_device(subdevice_id=client_id, hub=self, **client_data)
            self._sub_devices[client_id] = subdev

            # Trigger specific status update
            subdev.update_all()

        subdev.handle_push_event(client_data, namespace)

    def _get_status_impl(self):
        res = {}
        data = self.get_sys_data()['all']
        hub_data = data.get('digest').get('hub')
        res['hub_id'] = hub_data.get('hubId')
        res['mode'] = hub_data.get('mode')
        for subdevice in hub_data.get('subdevice'):
            self._update_subdevice_data(subdevice, None)
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

        def update_and_fire_event(subdevice_data, namespace):
            subdevice_id = subdevice_data.get('id')
            self._update_subdevice_data(subdevice_data, namespace)
            fire_hub_state_change(self, subdevice_id, self.get_subdevice_state(subdevice_id), from_myself)

        with self._state_lock:
            if namespace == HUB_TOGGLEX:
                for sensor_data in payload['togglex']:
                    update_and_fire_event(sensor_data, namespace)

            elif namespace == REPORT:
                pass

            elif namespace == HUB_MTS100_MODE:
                for sensor_data in payload['mode']:
                    update_and_fire_event(sensor_data, namespace)

            # Target temperature set on the device
            elif namespace == HUB_MTS100_TEMPERATURE:
                for sensor_data in payload['temperature']:
                    update_and_fire_event(sensor_data, namespace)

            else:
                l.warn("Unknown/Unsupported namespace/command: %s" % namespace)

    def _togglex(self, subdevice_id, status, channel=0, callback=None):
        payload = {'togglex': [{'id': subdevice_id, "onoff": status, "channel": channel}]}
        return self.execute_command('SET', HUB_TOGGLEX, payload, callback=callback)

    def get_subdevice_state(self, subdevice_id):
        return self._sub_devices.get(subdevice_id)

    def get_subdevices(self):
        return self._sub_devices.keys()

    def turn_on_subdevice(self, subdevice_id, channel=0, callback=None):
        return self._togglex(subdevice_id, 1, channel, callback=callback)

    def turn_off_subdevice(self, subdevice_id, channel=0, callback=None):
        return self._togglex(subdevice_id, 0, channel, callback=callback)

    def __str__(self):
        self.get_status()
        base_str = super().__str__()
        with self._state_lock:
            if not self.online:
                return base_str
            # TODO: fix this method. We'd probably want to print some more meaningful info
            return "%s [ %s ]" % (base_str, ",".join(self.get_subdevices()))
