"""
This module contains the Mixins related to diffuser light functionalities.
"""

import logging
from typing import Optional, Dict

from meross_iot.controller.device import BaseDevice
from meross_iot.model.enums import Namespace, DiffuserLightMode
from meross_iot.model.typing import RgbTuple
from meross_iot.utilities.conversion import rgb_to_int, int_to_rgb

_LOGGER = logging.getLogger(__name__)


class DiffuserLightMixin(BaseDevice):
    """
    Handles the capabilities offered by `Namespace.DIFFUSER_LIGHT` namespace.
    """

    def __init__(self, device_uuid: str,
                 manager,
                 **kwargs):
        super().__init__(device_uuid=device_uuid, manager=manager, **kwargs)
        # Dictionary keeping the status for every channel
        self.__diffuser_light_status_by_channel: Dict[int, Dict] = {}

    # We don't override async_update, as the SYSTEM_ALL data brings all the necessary
    # info this mixin needs.

    async def async_handle_update(self, namespace: Namespace, data: dict) -> bool:
        locally_handled = False
        if namespace == Namespace.SYSTEM_ALL:
            diffuser_data = data['all']['digest']['diffuser']['light']
            for l in diffuser_data:
                channel = l['channel']
                self.__diffuser_light_status_by_channel[channel] = l
            locally_handled = True
        super_handled = await super().async_handle_update(namespace=namespace, data=data)
        return super_handled or locally_handled

    async def _async_handle_push_notification(self, namespace: Namespace, data: dict) -> bool:
        locally_handled = False

        if namespace == Namespace.DIFFUSER_LIGHT:
            _LOGGER.debug("%s handling push notification for namespace %s", self.__class__.__name__, namespace,
                          str(namespace))
            payload = data.get('light')
            if payload is None:
                _LOGGER.error(f"{self.__class__.__name__} could not find 'light' attribute in push notification data: "
                              f"{data}")
                locally_handled = False
            else:
                # Update the status of every channel that has been reported in this push
                # notification.
                for c in payload:
                    channel = c['channel']
                    self.__diffuser_light_status_by_channel[channel] = c
                locally_handled = True
        # Always call the parent handler when done with local specific logic. This gives the opportunity to all
        # ancestors to catch all events.
        parent_handled = await super()._async_handle_push_notification(namespace=namespace, data=data)
        return locally_handled or parent_handled

    def diffuser_light_get_mode(self, channel: int = 0, *args, **kwargs) -> DiffuserLightMode | None:
        """
        Returns the operating mode for this device
        :param channel: channel to fetch info from
        :return:
        """
        if not self.check_full_update_done():
            return None
        if channel not in self.__diffuser_light_status_by_channel:
            raise ValueError("Invalid or unsupported channel specified")
        mode = self.__diffuser_light_status_by_channel[channel].get("mode")
        if mode is None:
            return None
        else:
            return DiffuserLightMode(mode)

    def diffuser_light_get_brightness(self, channel: int = 0, *args, **kwargs) -> int | None:
        """
        Returns the current configured led brightness
        :param channel: channel index to fetch info from
        :return:
        """
        if not self.check_full_update_done():
            return None
        if channel not in self.__diffuser_light_status_by_channel:
            raise ValueError("Invalid or unsupported channel specified")
        return self.__diffuser_light_status_by_channel[channel].get("luminance")

    def diffuser_light_get_rgb_color(self, channel=0, *args, **kwargs) -> RgbTuple | None:
        """
        Returns the current RGB configuration of the device.
        :param channel: channel to control, defaults to 0.
        :return: a Tuple containing three integer 8bits values (red, green, blue)
        """
        if not self.check_full_update_done():
            return None
        if channel not in self.__diffuser_light_status_by_channel:
            raise ValueError("Invalid or unsupported channel specified")
        info = self.__diffuser_light_status_by_channel[channel].get('rgb')
        if info is None:
            return None
        return int_to_rgb(info)

    def diffuser_light_get_is_on(self, channel: int = 0, *args, **kwargs) -> bool | None:
        """
        Returns True if the light is ON, False otherwise.
        :param channel: channel to control, defaults to 0 (bulbs generally have only one channel)
        :return: current onoff state
        """
        if not self.check_full_update_done():
            return None
        if channel not in self.__diffuser_light_status_by_channel:
            raise ValueError("Invalid or unsupported channel specified")
        onoff = self.__diffuser_light_status_by_channel[channel].get('onoff')
        if onoff is None:
            return None
        return onoff == 1

    async def async_diffuser_light_set_light_mode(self, channel: int = 0, onoff: bool = None,
                                                  mode: DiffuserLightMode = None,
                                                  brightness: int = None, rgb: Optional[RgbTuple] = None,
                                                  timeout: Optional[float] = None, *args, **kwargs) -> None:
        """
        Sets the light mode for this device.
        :param channel: channel to configure
        :param onoff: when True, sets the light ON, otherwise OFF.
        :param mode: defines the operation mode for this light
        :param brightness: brightness value (from 0 to 100)
        :param rgb: tuple of three integers (each from 0 to 255) for red, green, blue
        :param timeout: command timeout
        :return:
        """
        light_payload = {'channel': channel}
        if mode is not None:
            light_payload['mode'] = mode.value
        if brightness is not None:
            light_payload['luminance'] = brightness
        if rgb is not None:
            light_payload['rgb'] = rgb_to_int(rgb)
        if onoff is not None:
            light_payload['onoff'] = 1 if onoff else 0
        payload = {'light': [light_payload]}
        await self._execute_command(method='SET',
                                    namespace=Namespace.DIFFUSER_LIGHT,
                                    payload=payload,
                                    timeout=timeout)
        # Immediately update local state
        if channel not in self.__diffuser_light_status_by_channel:
            self.__diffuser_light_status_by_channel[channel] = {}
        self.__diffuser_light_status_by_channel[channel].update(light_payload)

    async def async_diffuser_light_turn_on(self, channel:int=0, *args, **kwargs) -> None:
        """
        Turns on the light of the diffuser.
        :param channel:
        :param args:
        :param kwargs:
        :return:
        """
        await self.async_diffuser_light_set_light_mode(channel=channel, onoff=True)
        # No need to update local state as this is done by the set_light_mode method

    async def async_diffuser_light_turn_off(self, channel=0, *args, **kwargs) -> None:
        """
        Turns off the light of the diffuser
        :param channel:
        :param args:
        :param kwargs:
        :return:
        """
        await self.async_diffuser_light_set_light_mode(channel=channel, onoff=False)
        # No need to update local state as this is done by the set_light_mode method
