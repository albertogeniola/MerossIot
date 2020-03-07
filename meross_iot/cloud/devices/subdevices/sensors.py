from meross_iot.cloud.abilities import HUB_MS100_ALL, HUB_MS100_TEMPHUM, HUB_MS100_ALERT
from meross_iot.cloud.devices.subdevices.generic import GenericSubDevice
from meross_iot.logger import SENSORS_LOGGER as l
from meross_iot.meross_event import SensorTemperatureChange, SensorTemperatureAlert


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

        elif namespace == HUB_MS100_ALERT:
            self._raw_state['alert'] = self._alert_payload_to_dict({'alert': [payload]})
            evt = SensorTemperatureAlert(device=self,
                                         alert=self._raw_state.get('alert'),
                                         generated_by_myself=from_myself)
            self.fire_event(evt)
            return True

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


    # sensor alerts format seems to be:
	# {'alert': [{'id': 'xxxx',
	#             'temperature': [[0, min, low], [0, low, high], [0, high, max]]
	#             'humidity':    [[0, min, low], [0, low, high], [0, high, max]]}]}
    def _alert_payload_to_dict(self, payload):
        ca = payload.get('alert')
        if ca is not None:
            result = {'temperature': {'min':  ca[0]['temperature'][0][1] / 10, \
                                      'low':  ca[0]['temperature'][1][1] / 10, \
                                      'high': ca[0]['temperature'][1][2] / 10, \
                                      'max':  ca[0]['temperature'][2][2] / 10}, \
                      'humidity':    {'min':  ca[0]['humidity'][0][1] / 10, \
                                      'low':  ca[0]['humidity'][1][1] / 10, \
                                      'high': ca[0]['humidity'][1][2] / 10, \
                                      'max':  ca[0]['humidity'][2][2] / 10} }
        else:
            result = None
        return result


    def get_alert(self):
        if self._raw_state.get('alert') is None:
            payload = {'alert': [{'id': self.subdevice_id}]}
            self._raw_state['alert'] = self._alert_payload_to_dict(self.execute_command("GET", HUB_MS100_ALERT, payload))
        return self._raw_state.get('alert')


    def set_alert(self, temperature_low:float = None, temperature_high:float = None, humidity_low:float = None, humidity_high:float = None):
        ca = self.get_alert()
        temp_min = round(10 * ca['temperature']['min'])
        temp_max = round(10 * ca['temperature']['max'])
        if (temperature_low is not None):
            temp_low = min(max(round(10 * temperature_low), temp_min), temp_max)
        else:
            temp_low = round(10 * ca['temperature']['low'])
        if (temperature_high is not None):
            temp_high = min(max(round(10 * temperature_high), temp_low), temp_max)
        else:
            temp_high = round(10 * ca['temperature']['high'])
        hum_min = round(10 * ca['humidity']['min'])
        hum_max = round(10 * ca['humidity']['max'])
        if (humidity_low is not None):
            hum_low = min(max(round(10 * humidity_low), hum_min), hum_max)
        else:
            hum_low = round(10 * ca['humidity']['low'])
        if (humidity_high is not None):
            hum_high = min(max(round(10 * humidity_high), hum_low), hum_max)
        else:
            hum_high = round(10 * ca['humidity']['high'])
        payload = {'alert': [{'id': self.subdevice_id, 'temperature': [[0, temp_min, temp_low], [0, temp_low, temp_high], [0, temp_high,temp_max]], 'humidity': [[0, hum_min, hum_low], [0, hum_low, hum_high], [0, hum_high, hum_max]]}]}
        self.execute_command("SET", HUB_MS100_ALERT, payload)
