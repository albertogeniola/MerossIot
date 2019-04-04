from meross_iot.supported_devices.power_plugs import Device


class Mss110(Device):
    def _handle_toggle(self, message):
        # TODO: implement logic for handling multi-channel toggle
        return None
