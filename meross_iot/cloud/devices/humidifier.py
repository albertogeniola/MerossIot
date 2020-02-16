from enum import Enum

from meross_iot.cloud.abilities import *
from meross_iot.cloud.device import AbstractMerossDevice
from meross_iot.cloud.devices.light_bulbs import MODE_RGB, to_rgb, MODE_LUMINANCE, MODE_TEMPERATURE
from meross_iot.logger import HUMIDIFIER_LOGGER as l
from meross_iot.meross_event import HumidifierSpryEvent, HumidifierLightEvent
from meross_iot.utilities.conversion import int_to_rgb


class SprayMode(Enum):
    OFF = 0
    CONTINUOUS = 1
    INTERMITTENT = 2


class GenericHumidifier(AbstractMerossDevice):
    _raw_state = None

    def __init__(self, cloud_client, device_uuid, **kwords):
        super(GenericHumidifier, self).__init__(cloud_client, device_uuid, **kwords)

    def _handle_push_notification(self, namespace, payload, from_myself=False) -> bool:
        if namespace == SPRAY:
            spray_data = payload.get('spray')
            self._update_state(space='spray', data=spray_data)

            for el in spray_data:
                evt = HumidifierSpryEvent(device=self,
                                          spry_mode=SprayMode(el.get('mode')),
                                          channel=el.get('channel'),
                                          generated_by_myself=from_myself)
                self.fire_event(evt)
            return True
        elif namespace == LIGHT:
            data = payload.get('light')
            self._update_state(space='light', data=data)
            evt = HumidifierLightEvent(dev=self,
                                       channel=data.get('channel'),
                                       onoff=data.get('onoff'),
                                       rgb=int_to_rgb(data.get('rgb')),
                                       luminance=data.get('luminance'),
                                       generated_by_myself=from_myself)
            self.fire_event(evt)
            return True
        else:
            l.warn("Unknown event: %s" % namespace)
            return False

    def get_status(self, force_status_refresh=False):
        with self._state_lock:
            if force_status_refresh or\
                    self._raw_state is None or \
                    self._raw_state.get('spray') is None or \
                    self._raw_state.get('light') is None:
                self._get_status_impl()
        return self._raw_state

    def set_spray_mode(self, spray_mode, channel=0, callback=None):
        payload = {'spray': {'channel': channel, 'mode': spray_mode.value}}
        self.execute_command('SET', SPRAY, payload, callback=callback)

    def get_spray_mode(self, channel=0):
        spray_elements = self.get_status().get('spray')
        for el in spray_elements:
            if el.get('channel') == channel:
                return SprayMode(el.get('mode'))
        return None

    def get_light_state(self):
        light_state = self.get_status().get('light')
        return light_state

    def turn_on_light(self):
        return self.configure_light(onoff=1)

    def turn_off_light(self):
        return self.configure_light(onoff=0)

    def get_light_color(self):
        light = self.get_status().get('light')
        if light is None:
            return None
        rgb = light.get('rgb')
        return int_to_rgb(rgb)

    def configure_light(self, onoff=None, rgb=None, luminance=100, temperature=-1, gradual=0, channel=0):
        if rgb is not None and temperature != -1:
            l.error("You are trying to set both RGB and luminance values for this bulb. It won't work!")

        # Prepare a basic payload
        payload = {
            'light': {
                'channel': channel,
                'gradual': gradual
            }
        }

        if onoff is not None:
            payload['light']['onoff'] = onoff

        mode = 0
        if self.supports_mode(MODE_RGB) and rgb is not None:
            # Convert the RGB to integer
            color = to_rgb(rgb)
            payload['light']['rgb'] = color
            mode = mode | MODE_RGB

        if self.supports_mode(MODE_LUMINANCE) and luminance != -1:
            payload['light']['luminance'] = luminance
            mode = mode | MODE_LUMINANCE

        if self.supports_mode(MODE_TEMPERATURE) and temperature != -1:
            payload['light']['temperature'] = temperature
            mode = mode | MODE_TEMPERATURE

        payload['light']['capacity'] = mode
        self.execute_command(command='SET', namespace=LIGHT, payload=payload)

    def supports_mode(self, mode):
        return (self.get_abilities().get(LIGHT).get('capacity') & mode) == mode

    def _get_status_impl(self):
        data = self.get_sys_data()['all']

        # Update online status
        online_status = data.get('system', {}).get('online', {}).get('status')
        if online_status is not None:
            self.online = online_status == 1

        # Update specific device status
        digest = data.get('digest')
        with self._state_lock:
            self._raw_state = digest
        return digest

    def _update_state(self, space, data):
        with self._state_lock:
            if self._raw_state is None:
                self._raw_state = {}

            if space == 'spray':
                self._raw_state['spray'] = data
            elif space == 'light':
                self._raw_state['light'] = data
            else:
                l.warn("Unsupported namespace %s" % space)

