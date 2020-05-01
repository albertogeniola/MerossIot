from meross_iot.model.enums import OnlineStatus, Namespace
from meross_iot.model.push.generic import GenericPushNotification


class OnlinePushNotification(GenericPushNotification):
    def __init__(self, online_status: OnlineStatus):
        super().__init__(namespace=Namespace.ONLINE)
        self.online_status = online_status

    @classmethod
    def from_dict(cls, data: dict):
        online_data = data.get("online")
        status = OnlineStatus(online_data.get("status"))
        return OnlinePushNotification(online_status=status)
