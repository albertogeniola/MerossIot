from meross_iot.supported_devices.power_plugs import Device


class Mss425e(Device):

    def _get_status_impl(self):
        res = {}
        if self._hwversion.split(".")[0] >= "2":
            for c in self.get_sys_data()['all']['digest']['togglex']:
                res[c['channel']] = c['onoff'] == 1
        else:
            for c in self.get_sys_data()['all']['control']['toggle']:
                res[c['channel']] = c['onoff'] == 1
        return res

    # TODO Implement for all channels
    def _handle_toggle(self, message):
        return None

    def enable_usb(self):
        return self._channel_control_impl(4, 1)

    def disable_usb(self):
        return self._channel_control_impl(4, 0)
