from meross_iot.supported_devices.power_plugs import Device


ABILITY_TOGGLE = 'Appliance.Control.Toggle'

class Mss210(Device):
    def _get_status_impl(self):
        res = {}
        res[0] = self.get_sys_data()['all']['digest']['togglex'][0]['onoff'] == 1
        return res

    def _handle_toggle(self, message):
        if 'onoff' in message['payload']['toggle']:
            self._status = (message['payload']['toggle']['onoff'] == 1)