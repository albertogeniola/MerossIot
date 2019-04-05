from meross_iot.supported_devices.power_plugs import GenericPlug


class Mss425(GenericPlug):
    def __init__(self,
                 token,
                 key,
                 user_id,
                 **kwords):
        super().__init__(token,
                 key,
                 user_id,
                 **kwords)

    def enable_usb(self):
        return self.turn_on_channel(4)

    def disable_usb(self):
        return self.turn_off_channel(4)


class Mss425e(Mss425):
    pass