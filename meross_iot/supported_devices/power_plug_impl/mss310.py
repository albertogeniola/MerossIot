from meross_iot.supported_devices.power_plugs import Device


class Mss310(Device):
    def _get_status_impl(self):
        res = {}
        if self._hwversion.split(".")[0] >= "2":
            res[0] = self.get_sys_data()['all']['digest']['togglex'][0]['onoff'] == 1
        else:
            res = {}
            res[0] = self.get_sys_data()['all']['control']['toggle']['onoff'] == 1
        return res

    def _handle_toggle(self, message):
        #TODO
        if 'onoff' in message['payload']['toggle']:
            self._status = (message['payload']['toggle']['onoff'] == 1)

    def get_electricity(self):
        return self._execute_cmd("GET", "Appliance.Control.Electricity", {})

    def get_power_consumptionX(self):
        return self._execute_cmd("GET", "Appliance.Control.ConsumptionX", {})
