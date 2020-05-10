from __future__ import annotations

import logging
from typing import List, Union

from meross_iot.model.enums import OnlineStatus, Namespace
from meross_iot.model.http.device import HttpDeviceInfo
from meross_iot.model.push.generic import GenericPushNotification

_LOGGER = logging.getLogger(__name__)


class BaseMerossDevice(object):
    def __init__(self, device_uuid: str,
                 manager,  # TODO: type hinting "manager"
                 **kwargs):
        self.uuid = device_uuid
        self._manager = manager
        self._channels = self._parse_channels(kwargs.get('channels', []))

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

    @property
    def channels(self) -> List[ChannelInfo]:
        return self._channels

    def update_from_http_state(self, hdevice: HttpDeviceInfo) -> None:
        # TODO: update local name/hwversion/fwversion/online-status from online http information
        # Careful with online  status: not all the devices might expose an online mixin.
        raise Exception("Not implemented yet!")

    def handle_push_notification(self, push_notification: GenericPushNotification) -> bool:
        # By design, the base class does not implement any push notification.
        _LOGGER.debug(f"MerossBaseDevice {self.name} handling notification {push_notification.namespace}")
        return False

    def handle_update(self, data: dict) -> None:
        # By design, the base class doe snot implement any update logic
        # TODO: we might update name/uuid/other stuff in here...
        pass

    async def async_update(self) -> None:
        # This method should be overridden implemented by mixins and never called directly. Its main
        # objective is to call the corresponding GET ALL command, which varies in accordance with the
        # device type. For instance, wifi devices use GET System.Appliance.ALL while HUBs use a different one.
        # Implementing mixin should never call the super() implementation (as it happens
        # with _handle_update) as we want to use only an UPDATE_ALL method.
        # However, we want to keep it within the MerossBaseDevice so that we expose a consistent
        # interface.
        raise NotImplementedError("This method should never be called on the BaseMerossDevice. If this happens,"
                                  "it means there is a device which is not being attached any update mixin."
                                  f"Contact the developer. Current object bases: {self.__class__.__bases__}")

    async def _execute_command(self, method: str, namespace: Namespace, payload: dict) -> dict:
        return await self._manager.async_execute_cmd(destination_device_uuid=self.uuid,
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

    @staticmethod
    def _parse_channels(channel_data: List) -> List[ChannelInfo]:
        res = []
        if channel_data is None:
            return res

        for i, val in enumerate(channel_data):
            name = val.get('name')
            type = val.get('type')
            master = i == 0
            res.append(ChannelInfo(index=i, name=name, channel_type=type, is_master_channel=master))

        return res

    def lookup_channel(self, channel_id_or_name: Union[int, str]):
        res = []
        if isinstance(channel_id_or_name, str):
            res = list(filter(lambda c: c.name == channel_id_or_name, self._channels))
        elif isinstance(channel_id_or_name, int):
            res = list(filter(lambda c: c.index == channel_id_or_name, self._channels))
        if len(res) == 1:
            return res[0]
        raise ValueError(f"Could not find channel by id or name = {channel_id_or_name}")


class ChannelInfo(object):
    def __init__(self, index: int, name: str = None, channel_type: str = None, is_master_channel:bool = False):
        self._index = index
        self._name = name
        self._type = channel_type
        self._master = is_master_channel

    @property
    def index(self) -> int:
        return self._index

    @property
    def is_usb(self) -> bool:
        return self._type == 'USB'

    @property
    def is_master_channel(self) -> bool:
        return self._master

