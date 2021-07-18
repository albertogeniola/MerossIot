from meross_iot.model.enums import Namespace
from meross_iot.model.push.generic import GenericPushNotification


class UnbindPushNotification(GenericPushNotification):
    def __init__(self, originating_device_uuid: str, raw_data: dict):
        super().__init__(namespace=Namespace.CONTROL_UNBIND, originating_device_uuid=originating_device_uuid, raw_data=raw_data)
