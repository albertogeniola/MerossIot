"""
The device module contains the base classes for handling Meross devices.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import List, Union, Optional, Callable, Awaitable, Dict, Any
from typing import TYPE_CHECKING
from meross_iot.model.constants import DEFAULT_MQTT_PORT, DEFAULT_MQTT_HOST, DEFAULT_COMMAND_TIMEOUT
from meross_iot.model.enums import OnlineStatus, Namespace
from meross_iot.model.http.device import HttpDeviceInfo
from meross_iot.model.http.subdevice import HttpSubdeviceInfo
from meross_iot.utilities.network import extract_domain, extract_port


DISABLE_ASYNC_UPDATE_WARNING = False


if TYPE_CHECKING:
    from meross_iot.controller.mixins.hub import HubMixin

_LOGGER = logging.getLogger(__name__)


class BaseDevice:
    """
    A `BaseDevice` is a generic representation of a Meross device.
    Any BaseDevice is characterized by some generic information, such as user's defined
    name, type (i.e. device specific model), firmware/hardware version, a Meross internal
    identifier, a library assigned internal identifier.

    The BaseDevice class takes care of handling internal device state in dynamic way.
    Each BaseDevice instance can be specialized via Mixins, which defines "pluggable" behaviour based
    on device abilities, fetched via the GET Ability command, via MQTT.

    Each Mixin can override the following methods
    - async_update()
      Used to trigger an update of the device. Usually, Mixins won't need to issue dedicated updates: the
      SYSTEM_ALL MixIn would generally collect the entire state and let all mixin parse their portion of
      the state, by calling async_handle_update(). However, there might be edge cases in which this
      is not enough (SubDevices): in such cases, we can issue additional update commands within
      this method to ensure a complete state update.

    - async_handle_update()
      This method is called by the SYSTEM_ALL mixin, when a fresh state has been requested/fetched.
      Mixins can override this method and parse the portion of the SYTEM_ALL payload they
      are interested into, and update the internal state representation.
      Mixins **must always** call the super() implementation to ensure correct event bubbling, and
      give the opportunity to other mixin in the __mro__ to handle the state change.
      This method is **not intended to deal with push notifications**, for that rely on
      `_async_handle_push_notification`, instead.
      The BaseDevice class uses this method to take track of "last full update" received (this is one
      of the reasons why each subclass must always call the super().async_handle_update implementation).

    - async_dispatch_push_notification()
      Called by the `MerossManager` whenever a push notification is received for this device.
      This method is usually used by the Manager or by the HubMixin to deliver push notifications
      to devices and SubDevices.

    - _async_handle_push_notification():
      This method can be overridden by Mixins in order to handle PushNotification data.
      Internally, this method is called by async_dispatch_push_notification(), before any registered
      event handler is Notified. In this way, Devices and SubDevices are expected to provide
      updated data when push notifications are handled by external handlers (registered by the user).

    """
    _name: str = "unknown"
    _type: str = "unknown"
    _fwversion: str = "unknown"
    _hwversion: str = "unknown"
    _online: OnlineStatus = OnlineStatus.UNKNOWN
    _inner_ip: str | None = None
    _mac_address: str | None = None
    _mqtt_host: str = DEFAULT_MQTT_HOST
    _mqtt_port: int = DEFAULT_MQTT_PORT

    def __init__(self, device_uuid: str,
                 manager,
                 **kwargs):
        self._manager = manager
        self._channels: List[ChannelInfo] = []
        self._push_coros: List[Callable[[str, dict, str], Awaitable]] = []
        self._last_full_update_ts: int | None = None
        self._abilities: Dict[str, str] = {}

        self._uuid = device_uuid
        self._cached_http_info: HttpDeviceInfo | None = None

        if 'http_device_info' in kwargs:
            self.update_from_http_state(kwargs['http_device_info'])
        if hasattr(self, "_abilities_spec"):
            self._abilities = self._abilities_spec

        # Set default timeout value for command execution
        self._timeout = DEFAULT_COMMAND_TIMEOUT

    @property
    def cached_http_info(self) -> HttpDeviceInfo | None:
        """The cached http info as returned by the Meross API"""
        return self._cached_http_info

    @property
    def lan_ip(self) -> str | None:
        """
        The LAN IP address of the device. This is known only after a full update.
        Ony the devices equipped with a WIFI radio will have this information.
        For SubDevice this value is None.
        """
        return self._inner_ip

    @property
    def mac_address(self) -> str | None:
        """
        The MAC ADDRESS of the device. This is known only after a full update.
        Ony the devices equipped with a WIFI radio will have this information.
        For SubDevice this value is None.
        """
        return self._mac_address

    @property
    def mqtt_host(self) -> str | None:
        """
        Host name of the Meross MQTT server that this device should use.
        The host assigned is generally provided via HTTP APIs, after the login.
        :return:
        """
        return self._mqtt_host

    @property
    def mqtt_port(self) -> int | None:
        """
        MQTT Host port of the Meross MQTT server that this device should use.
        This is provided via HTTP APIs, after the login.
        :return:
        """
        return self._mqtt_port

    @property
    def abilities(self) ->  Dict[str, str]:
        """
        List of Meross abilities as provided by the Meross API.
        :return:
        """
        return self._abilities

    @property
    def last_full_update_timestamp(self) -> int | None:
        """
        Timestamp when the last full update was received.
        Timestamp is in seconds.
        :return:
        """
        return self._last_full_update_ts

    def check_full_update_done(self) -> bool:
        """
        Returns True if a full update was ever performed.
        Note: this does not guarantee that the data is fresh.
        Check `last_full_update_timestamp` for that.
        :return:
        """
        update_done = self._last_full_update_ts is not None
        if not update_done and not DISABLE_ASYNC_UPDATE_WARNING:
            _LOGGER.warning(f"Please invoke async_update() for this device ({self._name}) "
                          "before accessing its state. Failure to do so may result in inconsistent state.")
        return update_done

    def register_push_notification_handler_coroutine(self, coro: Callable[[str, dict, str], Awaitable]) -> None:
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

    def unregister_push_notification_handler_coroutine(self, coro: Callable[[str, dict, str], Awaitable]) -> None:
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

    async def _fire_push_notification_event(self, namespace: Namespace, data: Any, device_internal_id: str):
        for c in self._push_coros:
            try:
                await c(namespace=namespace, data=data, device_internal_id=device_internal_id)  # type: ignore
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

    def update_from_http_state(self, hdevice: HttpDeviceInfo) -> BaseDevice:
        # Careful with online  status: not all the devices might expose an online mixin.
        if hdevice.uuid != self.uuid:
            raise ValueError(f"Cannot update device ({self.uuid}) with HttpDeviceInfo for device id {hdevice.uuid}")

        self._cached_http_info = hdevice
        self._channels = self._parse_channels(hdevice.channels)
        self._name = hdevice.dev_name
        self._type = hdevice.device_type
        self._fwversion = hdevice.fmware_version
        self._hwversion = hdevice.hdware_version
        self._online = hdevice.online_status

        # Domain and port parsing
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

        return self

    async def _async_handle_push_notification(self, namespace: Namespace, data: Any) -> bool:
        """
        Handles push notification updates
        :param namespace: Push notification header
        :param data: Push notification data
        :return:
        """
        _LOGGER.debug(f"MerossBaseDevice {self.name} handling notification {namespace} -> {data}")

        # The base implementation will just return FALSE, as we do not handle any push notification within the base-class
        return False

    async def async_dispatch_push_notification(self, namespace: Namespace, data: Any) -> bool:
        """
        Delivers a push notification to the device, so that it can update its internal state
        :param namespace: Push notification header
        :param data: Push notification data
        :return: True if the dispatching has been handled correctly. Returns False if the push notification is unhandled
        """
        # Let the current implementation handle the push notification
        handled = await self._async_handle_push_notification(namespace=namespace, data=data)

        # Once the notification has been handled, fire the push-notification handler to notify all the listeners
        #  that are registered on this specific event on this device
        await self._fire_push_notification_event(namespace=namespace, data=data, device_internal_id=self.internal_id)

        return handled

    async def async_handle_update(self, namespace: Namespace, data: dict) -> bool:
        """
        Handles the update dispatched by the specific namespace.
        It is generally used by some mixins such as SystemAllMixin to broadly
        propagate the data updates on each instance.

        Note: this method is not intended to deal with push notifications, for that rely on
        `_async_handle_push_notification`.
        :param namespace: Namespace describing the data payload to handle (result of a GET <NAMESPACE> command).
        :param data: Result of the command
        :return: True if the dispatching has been handled correctly. Returns False if the update is unhandled
        """
        # The Base implementation only takes care of updating inner_ip and mac_address from
        # system_all mixin.
        if namespace == Namespace.SYSTEM_ALL:
            # TODO: we might update name/uuid/other stuff in here...
            system = data.get('all', {}).get('system', {})
            self._inner_ip = system.get('firmware', {}).get('innerIp')
            self._mac_address = system.get('hardware', {}).get('macAddress', None)
            if self._mac_address is not None:
                self._mac_address = self._mac_address.lower()

        self._last_full_update_ts = int(time.time() * 1000)

        # Even though we handle the event, we return False as we did not handle the event in any way
        # rather than updating the last_full_update_ts
        return False

    async def async_update(self,
                           *args,
                           **kwargs) -> None:
        """
        Forces a full data update on the device. If your network bandwidth is limited or if you are running
        this program on an embedded device, try to invoke this method only when strictly needed.
        Most of the parameters of a device are updated automatically upon push-notification received
        by the meross MQTT cloud.
        :return: None
        """
        # The BaseDevice implementation does basically nothing. The update is handled generally by
        # mixin classes. Specifically, Wifi-equipped devices usually rely on the SystemAll Mixin.
        # Other subclasses might need to override this method to prevent or specialize the default behavior.
        pass

    def dismiss(self) -> None:
        """
        Perform necessary memory disposal operations on this instance to
        ensure graceful clean up.
        :return:
        """
        self._push_coros.clear()
        pass

    @property
    def default_command_timeout(self) -> float:
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


class GenericSubDevice(BaseDevice):
    """
    A SubDevice is a device that is not capable of handling direct communication with
    the cloud or via HTTP. It is generally battery powered and equipped with low-power
    radio and communicates with one HUB.
    """

    def __init__(self, hubdevice_uuid: str, subdevice_id: str, status: int, last_active_time: int, manager,
                 subdevice_name: str = 'not_discovered', subdevice_type: str = 'not_discovered',
                 subdevice_true_id: str = 'not_discovered',
                 vendor: str = 'not_discovered', **kwargs):
        hubs = manager.find_devices(device_uuids=(hubdevice_uuid,))  # type: List[HubMixin]
        if len(hubs) < 1:
            raise ValueError("Specified hub device is not present")
        hub = hubs[0]
        super().__init__(device_uuid=hubdevice_uuid, manager=manager, domain=hub.mqtt_host, port=hub.mqtt_port,
                         **kwargs)
        self._subdevice_id = subdevice_id
        self._type = subdevice_type
        self._name = subdevice_name
        self._online = OnlineStatus(status)
        self._last_active_time = last_active_time
        self._hub = hub
        self._vendor = vendor
        self._subdevice_true_id = subdevice_true_id
        self._fwversion = kwargs.get('firmware', 'unknown')
        self._hwversion = kwargs.get('hardware', 'unknown')

    def update_subdevice_from_http_state(self, device_info: HttpSubdeviceInfo):
        self._name = device_info.sub_device_name
        self._type = device_info.sub_device_type
        self._vendor = device_info.sub_device_vendor
        self._subdevice_true_id = device_info.true_id

    async def _execute_command(self,
                               method: str,
                               namespace: Namespace,
                               payload: dict,
                               timeout: Optional[float] = None
                               ) -> dict:
        # SubDevices talk to the meross cloud using the HUB.
        return await self._hub._execute_command(method=method, namespace=namespace, payload=payload, timeout=timeout)

    async def async_notify_hub_update(self, data: Dict) -> bool:
        """
        This method must be called by the HubMixin whenever a full update (SYSTEM_ALL) is received at hub-level.
        This allows the library to be more efficient: whenever you need to update the state of all SubDevices
        attached to a hub, just call the hub's async_update() and that will fetch and update the state of
        all related SubDevices.
        :param data: Contains the data as per SYSTEM_ALL digest key.
        :return: True if the state was handled, False otherwise
        """
        # The base handler will just update the online and lastActiveTime, if available
        # Handling both the "online" push notification and the "system_all" "status" notification
        locally_handled = False
        if 'status' in data:
            self._online = OnlineStatus(data['status'])
        if 'lastActiveTime' in data:
            self._last_active_time = data['lastActiveTime']
            locally_handled = True

        # The base handler, will just do nothing.
        return locally_handled

    async def _async_handle_push_notification(self, namespace: Namespace, data: Any) -> bool:
        """
        Handles SubDevice state update based on PushNotifications.
        Mixins can override this method in order to catch specific PushNotifications
        and update their internal state accordingly.
        :param namespace:
        :param data:
        :return:
        """

        # Mixins are not able to receive push notifications via MQTT/HTTP.
        # This method is called via dispatch_push_notification() at HubMixin level
        parent_handled = await super()._async_handle_push_notification(namespace=namespace, data=data)
        locally_handled = False
        if namespace in (Namespace.SYSTEM_ONLINE, Namespace.HUB_ONLINE):
            self._online = OnlineStatus(data['online']['status'])
            self._last_active_time = data['online']['lastActiveTime']
            locally_handled = True
        elif namespace == Namespace.HUB_UNBIND:
            self._online = OnlineStatus.UNKNOWN
            locally_handled = True

        return parent_handled or locally_handled

    @property
    def internal_id(self) -> str:
        """
        Internal ID created by this library for this device.
        :return:
        """
        return f"#BASE:{self._uuid}#SUB:{self._subdevice_id}"

    @property
    def subdevice_id(self):
        """
        Meross SubDevice ID.
        :return:
        """
        return self._subdevice_id


class ChannelInfo:
    def __init__(self, index: int, name: str | None = None, channel_type: str | None = None, is_master_channel: bool = False):
        self._index = index
        self._name = name
        self._type = channel_type
        self._master = is_master_channel

    @property
    def index(self) -> int:
        """
        Index of the channel.
        :return:
        """
        return self._index

    @property
    def is_usb(self) -> bool:
        """
        True if the channel type is USB.
        :return:
        """
        return self._type == 'USB'

    @property
    def is_master_channel(self) -> bool:
        """
        True if this represents the master channel of the device.
        :return:
        """
        return self._master

    @property
    def name(self) -> str | None:
        """
        Name of the channel.
        :return:
        """
        return self._name
