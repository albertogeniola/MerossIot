from abc import ABC, abstractmethod

from meross_iot.model.enums import OnlineStatus, Namespace
from meross_iot.model.http.device import HttpDeviceInfo
from meross_iot.model.push.generic import AbstractPushNotification
from meross_iot.model.push.online import OnlinePushNotification
import logging


_LOGGER = logging.getLogger(__name__)


class BaseMerossDevice(object):
    def __init__(self, device_uuid: str,
                 manager,  # TODO: type hinting "manager"
                 **kwargs):
        super().__init__()
        self.uuid = device_uuid
        self._manager = manager
        self._channels = kwargs.get('channels', [])

        # Information about device
        self._name = kwargs.get('devName')
        self._type = kwargs.get('deviceType')
        self._fwversion = kwargs.get('fmwareVersion')
        self._hwversion = kwargs.get('hdwareVersion')
        self._online = OnlineStatus(kwargs.get('onlineStatus'))

        # TODO: decide how to handle this
        self._abilities = None

    @property
    def name(self) -> str:
        return "unknown" if self._name is None else self._name

    @property
    def type(self) -> str:
        return "unknown" if self._type is None else self._type

    @property
    def firmware_version(self) -> str:
        return "unknown" if self._fwversion is None else self._fwversion

    @property
    def hardware_version(self) -> str:
        return "unknown" if self._hwversion is None else self._hwversion

    @property
    def online_status(self) -> OnlineStatus:
        return self._online

    def update_from_http_state(self, hdevice: HttpDeviceInfo) -> None:
        # TODO: update local name/hwversion/fwversion/online-status from online http information
        raise Exception("Not implemented yet!")

    async def handle_push_notification(self, push_notification: AbstractPushNotification) -> bool:
        _LOGGER.debug(f"Device {self.name} handling notification {push_notification.namespace}")
        root_handled = False

        if isinstance(push_notification, OnlinePushNotification):
            self._online = push_notification.online_status

        # TODO: handle generic push notification valid for all devices,
        #  such as Bind/Unbind/Online
        #specific_handled = await self._handle_push_notification(push_notification)
        #return root_handled or specific_handled
        return False

    async def _execute_command(self, method: str, namespace: Namespace, payload: dict):
        await self._manager.async_execute_cmd(destination_device_uuid=self.uuid,
                                              method=method,
                                              namespace=namespace,
                                              payload=payload)

    def __str__(self) -> str:
        basic_info = "%s (%s, HW %s, FW %s): " % (
            self.name,
            self.type,
            self.hardware_version,
            self.firmware_version
        )

        return basic_info
