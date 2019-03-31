from meross_iot.supported_devices.power_plugs import Device


class Mss110(Device):
    def _handle_toggle(self, message):
        # TODO: implement logic for handling multi-channel toggle
        return None

    # TODO Implement for all channels
    def get_status(self):
        # TODO: implement logic for handling multi-channel status
        return None

    def turn_on(self):
        self._status = True
        payload = {'togglex':{"onoff":1}}
        return self._execute_cmd("SET", "Appliance.Control.ToggleX", payload)

    def turn_off(self):
        self._status = False
        payload = {'togglex':{"onoff":0}}
        return self._execute_cmd("SET", "Appliance.Control.ToggleX", payload)