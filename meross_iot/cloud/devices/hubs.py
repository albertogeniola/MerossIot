from threading import RLock

from meross_iot.cloud.abilities import *
from meross_iot.cloud.device import AbstractMerossDevice
from meross_iot.logger import POWER_PLUGS_LOGGER as l
from meross_iot.meross_event import DeviceHubStatusEvent
from meross_iot.cloud.devices.subdevices.generic import GenericSubDevice
from meross_iot.cloud.devices.subdevices.thermostats import ValveSubDevice


class GenericHub(AbstractMerossDevice):
    # Handles the state of this specific HUB
    _state = {}
    _sub_devices = {}
    _subdev_lock = None

    def __init__(self, cloud_client, device_uuid, **kwords):
        super(GenericHub, self).__init__(cloud_client, device_uuid, **kwords)
        self._subdev_lock = RLock()

    def register_sub_device(self,
                            subdev  # type: GenericSubDevice
                            ):
        with self._subdev_lock:
            if subdev.uuid != self.uuid:
                raise Exception("You cannot register this device to this hub, since it has been assigned a different "
                                "hub device uuid.")
            self._sub_devices[subdev.subdevice_id] = subdev

    def _update_subdevice_data(self, subdevice):
        # TODO
        pass

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
        base_str = super().__str__()
        with self._state_lock:
            if not self.online:
                return base_str
            # TODO: fix this method. We'd probably want to print some more meaningful info
            return base_str
