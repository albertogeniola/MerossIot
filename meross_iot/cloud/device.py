from abc import ABC, abstractmethod
from meross_iot.model.push.generic import AbstractPushNotification


class AbstractMerossDevice(ABC):
    def __init__(self,
                 device_uuid: str,
                 manager,  # TODO: find a way for set typing hints here
                 **kwargs):
        self.uuid = device_uuid
        self._manager = manager
        self._channels = kwargs.get('channels', [])

        # Information about device
        self.name = kwargs.get('devName')
        self.type = kwargs.get('deviceType')
        self.fwversion = kwargs.get('fmwareVersion')
        self.hwversion = kwargs.get('hdwareVersion')
        self.online = kwargs.get('onlineStatus') == 1

        self._abilities = None

    async def handle_push_notification(self, push_notification: AbstractPushNotification) -> bool:
        root_handled = False
        # TODO: handle generic push notification valid for all devices,
        #  such as Bind/Unbind/Online
        specific_handled = await self._handle_push_notification(push_notification)
        return root_handled or specific_handled

    @abstractmethod
    async def _handle_push_notification(self, push_notification: AbstractPushNotification) -> bool:
        pass

    def __str__(self):
        basic_info = "%s (%s, HW %s, FW %s): " % (
            self.name,
            self.type,
            self.hwversion,
            self.fwversion
        )

        return basic_info
