from meross_iot.model.enums import Namespace
from meross_iot.model.push.generic import GenericPushNotification


class UnbindPushNotification(GenericPushNotification):
    def __init__(self):
        super().__init__(namespace=Namespace.UNBIND)

    @classmethod
    def from_dict(cls, data: dict):
        return UnbindPushNotification()
