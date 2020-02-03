from enum import Enum
from meross_iot.cloud.abilities import HUB_MS100_ALL, HUB_MS100_TEMPHUM
from meross_iot.cloud.devices.subdevices.generic import GenericSubDevice
from meross_iot.logger import SENSORS_LOGGER as l
from meross_iot.meross_event import DeviceSwitchStatusEvent, SensorTemperatureChange, DeviceOnlineStatusEvent


class SensorSubDevice(GenericSubDevice):

    def __init__(self, cloud_client, subdevice_id, parent_hub, **kwords):
        super().__init__(cloud_client, subdevice_id, parent_hub, **kwords)

    def _handle_push_notification(self, namespace, payload, from_myself=False):
        # Let the Generic handler to handle the common events.
        handled = super()._handle_push_notification(namespace=namespace, payload=payload, from_myself=from_myself)
        if handled:
            return True

        # If the parent handler was unable to parse it, we do it here.
        evt = None
        if namespace == HUB_MS100_ALL:
            self._raw_state.update(payload)
            return True

        elif namespace == HUB_MS100_TEMPHUM:
            temp = self._raw_state.get('temperature')
            if temp is None:
                temp = {}
                self._raw_state['temperature'] = temp
            temp.update(payload)
            hum = self._raw_state.get('humidity')
            if hum is None:
                hum = {}
                self._raw_state['humidity'] = hum
            hum.update(payload)
            evt = SensorTemperatureChange(device=self,
                                              temperature_state=self._raw_state.get('temperature'),
                                              humidity_state=self._raw_state.get('humidity'),
                                              generated_by_myself=from_myself)
            self.fire_event(evt)
            return True

        # TODO: handle TIME SYNC event?
        # elif namespace == HUB_TIME_SYNC:
        #    self._state.get('??').update(payload)

        else:
            l.warn("Unsupported/unhandled event: %s" % namespace)
            l.debug("Namespace: %s, Data: %s" % (namespace, payload))
            return False

    @property
    def _status_token(self):
        return HUB_MS100_ALL

    @property
    def temperature(self):
        temp = self._get_property('temperature', 'latest')
        if temp is None:
            return None
        else:
            return temp / 10

    @property
    def humidity(self):
        humidity = self._get_property('humidity', 'latest')
        if humidity is None:
            return None
        else:
            return humidity / 10


