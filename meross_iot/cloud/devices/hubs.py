from threading import RLock

from meross_iot.cloud.abilities import *
from meross_iot.cloud.device import AbstractMerossDevice
from meross_iot.cloud.devices.subdevices.generic import GenericSubDevice
from meross_iot.logger import HUB_LOGGER as l


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

    def _get_status_impl(self):
        res = {}
        data = self.get_sys_data()['all']

        # Update online status
        online_status = data.get('system', {}).get('online', {}).get('status')
        if online_status is not None:
            self.online = online_status == 1

        # Update specific device state
        hub_data = data.get('digest').get('hub')
        res['hub_id'] = hub_data.get('hubId')
        res['mode'] = hub_data.get('mode')
        return res

    def get_status(self, force_status_refresh=False):
        with self._state_lock:
            if self._state == {} or force_status_refresh:
                self._state = self._get_status_impl()
            return self._state

    def _dispatch_event_to_subdevice(self, namespace, data, from_myself):
        target = None
        with self._subdev_lock:
            subdevice_id = data.get('id')
            target = self._sub_devices.get(subdevice_id)
            if target is None:
                return

            # Remove the id from the data payload as it will be stored as raw state from the device handler
            del data['id']
            target._handle_push_notification(namespace=namespace, payload=data, from_myself=from_myself)

    def _handle_push_notification(self, namespace, payload, from_myself=False):
        if namespace == HUB_ONLINE:
            for sensor_data in payload['online']:
                self._dispatch_event_to_subdevice(namespace=namespace, data=sensor_data, from_myself=from_myself)
            return True

        if namespace == HUB_TOGGLEX:
            for sensor_data in payload['togglex']:
                self._dispatch_event_to_subdevice(namespace=namespace, data=sensor_data, from_myself=from_myself)
            return True

        elif namespace == HUB_EXCEPTION:
            for ex in payload['exception']:
                self._dispatch_event_to_subdevice(namespace=namespace, data=ex, from_myself=from_myself)
            return True

        elif namespace == REPORT:
            l.info("Report event is currently unhandled")
            return False

        elif namespace == HUB_MTS100_MODE:
            for sensor_data in payload['mode']:
                self._dispatch_event_to_subdevice(namespace=namespace, data=sensor_data, from_myself=from_myself)
            return True

        elif namespace == HUB_MTS100_TEMPERATURE:
            for sensor_data in payload['temperature']:
                self._dispatch_event_to_subdevice(namespace=namespace, data=sensor_data, from_myself=from_myself)
            return True

        elif namespace == HUB_MS100_TEMPHUM:
            for sensor_data in payload['tempHum']:
                self._dispatch_event_to_subdevice(namespace=namespace, data=sensor_data, from_myself=from_myself)
            return True

        elif namespace == HUB_MS100_ALERT:
            for sensor_data in payload['alert']:
                self._dispatch_event_to_subdevice(namespace=namespace, data=sensor_data, from_myself=from_myself)
            return True

        else:
            l.error("Unknown/Unsupported namespace/command: %s" % namespace)
            l.debug("Namespace: %s, Data: %s" % (namespace, payload))
            return False

    def _togglex(self, subdevice_id, status, channel=0, callback=None):
        payload = {'togglex': [{'id': subdevice_id, "onoff": status, "channel": channel}]}
        return self.execute_command('SET', HUB_TOGGLEX, payload, callback=callback)

    def get_subdevice_state(self, subdevice_id):
        return self._sub_devices.get(subdevice_id)

    def get_subdevices(self):
        return self._sub_devices.keys()

    def get_subdevice(self, subdevice_id):
        return self._sub_devices.get(subdevice_id)

    def turn_on_subdevice(self, subdevice_id, channel=0, callback=None):
        return self._togglex(subdevice_id, 1, channel, callback=callback)

    def turn_off_subdevice(self, subdevice_id, channel=0, callback=None):
        return self._togglex(subdevice_id, 0, channel, callback=callback)

    def __str__(self):
        self.get_status()
        base_str = super().__str__()
        if not self.online:
            return base_str
        # TODO: fix this method. We'd probably want to print some more meaningful info
        return "%s [ %s ]" % (base_str, ",".join(self.get_subdevices()))
