from meross_iot.supported_devices.power_plugs import Device


class Mss210(Device):
    def get_status(self):
        # TODO: check
        if self._status is None:
            # Mss310, firmware
            self._status = self.get_sys_data()['all']['control']['toggle']['onoff'] == 1
        return self._status

    def _handle_toggle(self, message):
        if 'onoff' in message['payload']['toggle']:
            self._status = (message['payload']['toggle']['onoff'] == 1)