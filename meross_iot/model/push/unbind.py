from meross_iot.model.enums import Namespace
from meross_iot.model.push.generic import AbstractPushNotification


class UnbindPushNotification(AbstractPushNotification):
    def __init__(self, originating_device_uuid: str):
        super().__init__(namespace=Namespace.UNBIND, originating_device_uuid=originating_device_uuid)

    @classmethod
    def from_dict(cls, data: dict, originating_device_uuid: str):
        return UnbindPushNotification(originating_device_uuid=originating_device_uuid)
