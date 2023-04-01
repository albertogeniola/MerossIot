from __future__ import annotations

import asyncio
import json
import logging
import time
from datetime import datetime
from typing import List, Union, Optional, Iterable, Callable, Awaitable, Dict

from meross_iot.model.constants import DEFAULT_MQTT_PORT, DEFAULT_MQTT_HOST, DEFAULT_COMMAND_TIMEOUT
from meross_iot.model.enums import OnlineStatus, Namespace
from meross_iot.model.http.device import HttpDeviceInfo
from meross_iot.model.plugin.hub import BatteryInfo
from meross_iot.utilities.network import extract_domain, extract_port

_LOGGER = logging.getLogger(__name__)


class BaseDevice(object):
    """
    A `BaseDevice` is a generic representation of a Meross device.
    Any BaseDevice is characterized by some generic information, such as user's defined
    name, type (i.e. device specific model), firmware/hardware version, a Meross internal
    identifier, a library assigned internal identifier.
    """
    _name: str = "unknown"
    _type: str = "unknown"
    _fwversion: str = "unknown"
    _hwversion: str = "unknown"
    _online: OnlineStatus = OnlineStatus.UNKNOWN
    _inner_ip: Optional[str] = None
    _mac_address: Optional[str] = None
    _mqtt_host: str = DEFAULT_MQTT_HOST
    _mqtt_port: int = DEFAULT_MQTT_PORT

    def __init__(self, device_uuid: str,
                 manager,
                 **kwargs):
        self._uuid = device_uuid
        self._manager = manager

        self._cached_http_info = None
        self._channels = []

        # Parse device info, if any
        if 'http_device_info' in kwargs:
            self._cached_http_info: HttpDeviceInfo = kwargs.get('http_device_info', {})
            self._channels = self._parse_channels(self._cached_http_info.channels)

            # Information about device
            self._name = self._cached_http_info.dev_name
            self._type = self._cached_http_info.device_type
            self._fwversion = self._cached_http_info.fmware_version
            self._hwversion = self._cached_http_info.hdware_version
            self._online = self._cached_http_info.online_status
            self._inner_ip = None

            # Domain and port
            domain = self._cached_http_info.domain
            reserved_domain = self._cached_http_info.reserved_domain

            # Prefer domain to reserved domain
            if domain is not None:
                self._mqtt_host = extract_domain(domain)
                self._mqtt_port = extract_port(domain, DEFAULT_MQTT_PORT)
            elif reserved_domain is not None:
                self._mqtt_host = extract_domain(reserved_domain)
                self._mqtt_port = extract_port(reserved_domain, DEFAULT_MQTT_PORT)
            else:
                _LOGGER.warning("No MQTT DOMAIN/RESERVED DOMAIN specified in args, assuming default value %s:%d",
                                DEFAULT_MQTT_HOST, DEFAULT_MQTT_PORT)

        if hasattr(self, "_abilities_spec"):
            self._abilities = self._abilities_spec
        else:
            self._abilities = {}
        self._push_coros = []
        self._last_full_update_ts = None

        # Set default timeout value for command execution
        self._timeout = DEFAULT_COMMAND_TIMEOUT

    @property
    def cached_http_info(self) -> Optional[HttpDeviceInfo]:
        return self._cached_http_info

    @property
    def lan_ip(self):
        return self._inner_ip

    @property
    def mac_address(self):
        return self._mac_address

    @property
    def mqtt_host(self):
        return self._mqtt_host

    @property
    def mqtt_port(self):
        return self._mqtt_port

    @property
    def abilities(self):
        return self._abilities

    @property
    def last_full_update_timestamp(self):
        return self._last_full_update_ts

    def check_full_update_done(self):
        update_done = self._last_full_update_ts is not None
        if not update_done:
            _LOGGER.error(f"Please invoke async_update() for this device ({self._name}) "
                          "before accessing its state. Failure to do so may result in inconsistent state.")
        return update_done

    def register_push_notification_handler_coroutine(self, coro: Callable[[Namespace, dict, str], Awaitable]) -> None:
        """
        Registers a coroutine so that it gets invoked whenever a push notification is
        delivered to this device or when the device state is changed.
        This allows the developer to "react" to notifications state change due to other users operating the device.
        :param coro: coroutine-function to invoke when the state changes.
        Its signature must be (namespace: Namespace, data: dict, device_internal_id: str)
        :return:
        """
        if not asyncio.iscoroutinefunction(coro):
            raise ValueError("The coro parameter must be a coroutine")
        if coro in self._push_coros:
            _LOGGER.error(f"Coroutine {coro} was already added to event handlers of this device")
            return
        self._push_coros.append(coro)

    def unregister_push_notification_handler_coroutine(self, coro: Callable[[Namespace, dict, str], Awaitable]) -> None:
        """
        Unregisters the event handler
        :param coro: coroutine-function: a function that, when invoked, returns a Coroutine object that can be awaited.
        This coroutine function should have been previously registered
        :return:
        """
        if coro in self._push_coros:
            self._push_coros.remove(coro)
        else:
            _LOGGER.error(f"Coroutine {coro} was not registered as handler for this device")

    async def _fire_push_notification_event(self, namespace: Namespace, data: dict, device_internal_id: str):
        for c in self._push_coros:
            try:
                await c(namespace=namespace, data=data, device_internal_id=device_internal_id)
            except Exception as e:
                _LOGGER.exception(f"Error occurred while firing push notification event {namespace} with data: {data}")

    @property
    def internal_id(self) -> str:
        """
        Internal ID used by this library to identify meross devices. It's basically composed by
        the Meross ID plus some prefix/suffix.
        :return:
        """
        return f"#BASE:{self._uuid}"

    @property
    def uuid(self) -> str:
        """
        Meross identifier of the device.
        :return:
        """
        return self._uuid

    @property
    def name(self) -> str:
        """
        User's defined name of the device
        :return:
        """
        return "unknown" if self._name is None else self._name

    @property
    def type(self) -> str:
        """
        Device model type
        :return:
        """
        return "unknown" if self._type is None else self._type

    @property
    def firmware_version(self) -> str:
        """
        Device firmware version. When unavailable, 'unknown' is returned
        :return:
        """
        return "unknown" if self._fwversion is None else self._fwversion

    @property
    def hardware_version(self) -> str:
        """
        Device hardware revision
        :return:
        """
        return "unknown" if self._hwversion is None else self._hwversion

    @property
    def online_status(self) -> OnlineStatus:
        """
        Current device online status
        :return:
        """
        return self._online

    @property
    def channels(self) -> List[ChannelInfo]:
        """
        List of channels exposed by this device. Multi-channel devices might expose a master
        switch at index 0.
        :return:
        """
        return self._channels

    async def update_from_http_state(self, hdevice: HttpDeviceInfo) -> BaseDevice:
        # Careful with online  status: not all the devices might expose an online mixin.
        if hdevice.uuid != self.uuid:
            raise ValueError(f"Cannot update device ({self.uuid}) with HttpDeviceInfo for device id {hdevice.uuid}")
        self._cached_http_info=hdevice
        self._cached_http_info = hdevice
        self._name = hdevice.dev_name
        self._channels = self._parse_channels(hdevice.channels)
        self._type = hdevice.device_type
        self._fwversion = hdevice.fmware_version
        self._hwversion = hdevice.hdware_version
        self._online = hdevice.online_status

        # TODO: fire some sort of events to let users see changed data?
        return self

    async def async_handle_push_notification(self, namespace: Namespace, data: dict) -> bool:
        _LOGGER.debug(f"MerossBaseDevice {self.name} handling notification {namespace}")

        # However, we want to notify any registered event handler
        await self._fire_push_notification_event(namespace=namespace, data=data, device_internal_id=self.internal_id)
        return False

    async def async_handle_update(self, namespace: Namespace, data: dict) -> bool:
        # Catch SYSTEM_ALL case and update the generic device info
        if namespace == Namespace.SYSTEM_ALL:
            # TODO: we might update name/uuid/other stuff in here...
            system = data.get('all', {}).get('system', {})
            self._inner_ip = system.get('firmware', {}).get('innerIp')
            self._mac_address = system.get('hardware', {}).get('macAddress', None)

        await self._fire_push_notification_event(namespace=namespace, data=data, device_internal_id=self.internal_id)
        self._last_full_update_ts = time.time() * 1000

        # Even though we handle the event, we return False as we did not handle the event in any way
        # rather than updating the last_full_update_ts
        return False

    async def async_update(self,
                           *args,
                           **kwargs) -> None:
        """
        Forces a full data update on the device. If your network bandwidth is limited or you are running
        this program on an embedded device, try to invoke this method only when strictly needed.
        Most of the parameters of a device are updated automatically upon push-notification received
        by the meross MQTT cloud.
        :return: None
        """
        """
        # This method should be overridden implemented by mixins and never called directly. Its main
        # objective is to call the corresponding GET ALL command, which varies in accordance with the
        # device type. For instance, wifi devices use GET System.Appliance.ALL while HUBs use a different one.
        # Implementing mixin should never call the super() implementation (as it happens
        # with _handle_update) as we want to use only an UPDATE_ALL method.
        # Howe                               ver, we want to keep it within the MerossBaseDevice so that we expose a consistent
        # interface.
        """
        pass

    def dismiss(self):
        # TODO: Should we do something here?
        pass

    @property
    def default_command_timeout(self):
        """
        Represents the default timeout that is applied to command execution against this device.
        Usually, every method allows to override this timeout via an appropriate timeout argument: that argument
        takes precedence over this default.
        """
        return self._timeout

    @default_command_timeout.setter
    def default_command_timeout(self, val: Union[float, int]):
        if val is None or val < 0:
            raise ValueError("Command execution timeout must a positive number")
        self._timeout = val

    async def _execute_command(self,
                               method: str,
                               namespace: Namespace,
                               payload: dict,
                               timeout: Optional[float] = None,
                               ) -> dict:
        if timeout is None:
            to = self.default_command_timeout
        else:
            to = timeout

        return await self._manager.async_execute_cmd(destination_device_uuid=self.uuid,
                                                     method=method,
                                                     namespace=namespace,
                                                     payload=payload,
                                                     timeout=to,
                                                     mqtt_hostname=self.mqtt_host,
                                                     mqtt_port=self.mqtt_port)

    def __repr__(self):
        basic_info = f"{self.name} ({self.type}, HW {self.hardware_version}, FW {self.firmware_version}, class: {self.__class__.__name__})"
        return basic_info

    @staticmethod
    def _parse_channels(channel_data: List) -> List[ChannelInfo]:
        res = []
        if channel_data is None:
            return res

        for i, val in enumerate(channel_data):
            name = val.get('devName', 'Main channel')
            type = val.get('type')
            master = i == 0
            res.append(ChannelInfo(index=i, name=name, channel_type=type, is_master_channel=master))

        return res

    def lookup_channel(self, channel_id_or_name: Union[int, str]):
        """
        Looks up a channel by channel id or channel name
        :param channel_id_or_name:
        :return:
        """
        res = []
        if isinstance(channel_id_or_name, str):
            res = list(filter(lambda c: c.name == channel_id_or_name, self._channels))
        elif isinstance(channel_id_or_name, int):
            res = list(filter(lambda c: c.index == channel_id_or_name, self._channels))
        if len(res) == 1:
            return res[0]
        raise ValueError(f"Could not find channel by id or name = {channel_id_or_name}")


class HubDevice(BaseDevice):
    # TODO: provide meaningful comment here describing what this class does
    #  Discvoery?? Bind/unbind?? Online??
    def __init__(self, device_uuid: str, manager, **kwargs):
        super().__init__(device_uuid, manager, **kwargs)
        self._sub_devices = {}

    def get_subdevices(self) -> Iterable[GenericSubDevice]:
        return self._sub_devices.values()

    def get_subdevice(self, subdevice_id: str) -> Optional[GenericSubDevice]:
        return self._sub_devices.get(subdevice_id)

    def register_subdevice(self, subdevice: GenericSubDevice) -> None:
        # If the device is already registed, skip it
        if subdevice.subdevice_id in self._sub_devices:
            _LOGGER.info(f"Subdevice {subdevice.subdevice_id} has been already registered to this HUB ({self.name})")
            return

        self._sub_devices[subdevice.subdevice_id] = subdevice


class GenericSubDevice(BaseDevice):
    _UPDATE_ALL_NAMESPACE = None

    def __init__(self, hubdevice_uuid: str, subdevice_id: str, manager, **kwargs):
        hubs = manager.find_devices(device_uuids=(hubdevice_uuid,))  # type: List[HubDevice]
        if len(hubs) < 1:
            raise ValueError("Specified hub device is not present")
        hub = hubs[0]
        super().__init__(device_uuid=hubdevice_uuid, manager=manager, domain=hub.mqtt_host, port=hub.mqtt_port,
                         **kwargs)
        self._subdevice_id = subdevice_id
        self._type = kwargs.get('subDeviceType')
        self._name = kwargs.get('subDeviceName')
        self._onoff = None
        self._mode = None
        self._temperature = None
        self._hub = hub

    async def _execute_command(self,
                               method: str,
                               namespace: Namespace,
                               payload: dict,
                               timeout: Optional[float] = None
                               ) -> dict:
        # Every command should be invoked via HUB?
        raise NotImplementedError("Subdevices should rely on Hub in order to send commands.")

    async def async_update(self,
                           timeout: Optional[float] = None,
                           *args,
                           **kwargs) -> None:
        """
        Perfoms a full device update of the device attributes.
        """
        if self._UPDATE_ALL_NAMESPACE is None:
            _LOGGER.error("GenericSubDevice does not implement any GET_ALL namespace. Update won't be performed.")
            pass

        # When dealing with hubs, we need to "intercept" the UPDATE()
        await super().async_update(*args, **kwargs)

        # When issuing an update-all command to the hub,
        # we need to query all sub-devices.
        result = await self._hub._execute_command(method="GET",
                                                  namespace=self._UPDATE_ALL_NAMESPACE,
                                                  payload={'all': [{'id': self.subdevice_id}]},
                                                  timeout=timeout)
        subdevices_states = result.get('all')
        for subdev_state in subdevices_states:
            subdev_id = subdev_state.get('id')

            if subdev_id != self.subdevice_id:
                continue
            await self.async_handle_subdevice_notification(namespace=self._UPDATE_ALL_NAMESPACE, data=subdev_state)
            break

    async def async_get_battery_life(self,
                                     timeout: Optional[float] = None,
                                     *args,
                                     **kwargs) -> BatteryInfo:
        """
        Polls the HUB/DEVICE to get its current battery status.
        :return:
        """
        data = await self._hub._execute_command(method='GET',
                                                namespace=Namespace.HUB_BATTERY,
                                                payload={'battery': [{'id': self.subdevice_id}]},
                                                timeout=timeout)
        battery_life_perc = data.get('battery', {})[0].get('value')
        timestamp = datetime.utcnow()
        return BatteryInfo(battery_charge=battery_life_perc, sample_ts=timestamp)

    async def async_handle_subdevice_notification(self, namespace: Namespace, data: dict) -> bool:
        _LOGGER.error("Unhandled/NotImplemented event handler for %s (data: %s) - Subdevice %s (hub %s)", namespace,
                      json.dumps(data), self.subdevice_id, self._hub.uuid)
        return False

    @property
    def internal_id(self) -> str:
        return f"#BASE:{self._uuid}#SUB:{self._subdevice_id}"

    @property
    def subdevice_id(self):
        return self._subdevice_id

    @property
    def online_status(self) -> OnlineStatus:
        # If the HUB device is offline, return offline
        if self._hub.online_status != OnlineStatus.ONLINE:
            return self._hub.online_status

        return self._online

    def _prepare_push_notification_data(self, data: dict, filter_accessor: str = None) -> Optional[Dict]:
        if filter_accessor is not None:
            # Operate only on relative accessor
            context = data.get(filter_accessor)
            if context is None:
                raise ValueError(
                    "Could not find accessor %s within data %s. This push notification will be ignored." % (
                        filter_accessor, str(data)))
            pertinent_notifications = filter(lambda n: n.get('id') == self.subdevice_id, context)
            next(pertinent_notifications, None)

        else:
            notification = data.copy()
            if 'id' in notification:
                if notification.get('id') != self.subdevice_id:
                    _LOGGER.error("Ignoring notification %s as it does not target "
                                  "to subdevice id %s", notification, self.subdevice_id)
                notification.pop('id')
            return notification


class ChannelInfo(object):
    def __init__(self, index: int, name: str = None, channel_type: str = None, is_master_channel: bool = False):
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

    @property
    def name(self) -> str:
        return self._name
