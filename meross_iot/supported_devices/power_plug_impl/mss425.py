from meross_iot.supported_devices.power_plugs import Device


class Mss425e(Device):
    # TODO Implement for all channels
    def _handle_toggle(self, message):
        return None

    # TODO Implement for all channels
    def get_status(self):
        return None

    def turn_on(self):
        payload = {'togglex': {"onoff": 1}}
        return self._execute_cmd("SET", "Appliance.Control.ToggleX", payload)

    def turn_off(self):
        payload = {'togglex': {"onoff": 0}}
        return self._execute_cmd("SET", "Appliance.Control.ToggleX", payload)

    def turn_on_channel(self, channel):
        payload = {'togglex': {'channel': channel, 'onoff': 1}}
        return self._execute_cmd("SET", "Appliance.Control.ToggleX", payload)

    def turn_off_channel(self, channel):
        payload = {'togglex': {'channel': channel, 'onoff': 0}}
        return self._execute_cmd("SET", "Appliance.Control.ToggleX", payload)

    def enable_usb(self):
        return self.turn_on_channel(4)

    def disable_usb(self):
        return self.turn_off_channel(4)