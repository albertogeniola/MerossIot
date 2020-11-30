import logging
from typing import Optional, Union

from meross_iot.controller.mixins.toggle import ToggleMixin, ToggleXMixin
from meross_iot.model.enums import Namespace, LightMode
from meross_iot.model.plugin.light import LightInfo
from meross_iot.model.typing import RgbTuple
from meross_iot.utilities.conversion import rgb_to_int

_LOGGER = logging.getLogger(__name__)


class LightMixin(object):
    """
    Mixin class that enables light control.
    """
    _execute_command: callable
    check_full_update_done: callable
    #async_handle_update: Callable[[Namespace, dict], Awaitable]

    def __init__(self, device_uuid: str,
                 manager,
                 **kwargs):
        super().__init__(device_uuid=device_uuid, manager=manager, **kwargs)

        # Dictionary keeping the status for every channel
        self._channel_light_status = {}

    async def async_handle_push_notification(self, namespace: Namespace, data: dict) -> bool:
        locally_handled = False

        if namespace == Namespace.CONTROL_LIGHT:
            _LOGGER.debug(f"{self.__class__.__name__} handling push notification for namespace {namespace}")
            payload = data.get('light')
            if payload is None:
                _LOGGER.error(f"{self.__class__.__name__} could not find 'light' attribute in push notification data: "
                              f"{data}")
                locally_handled = False
            else:
                # Update the status of every channel that has been reported in this push
                # notification.
                c = payload['channel']
                self._update_channel_status(channel=c,
                                            rgb=payload.get('rgb'),
                                            luminance=payload.get('luminance'),
                                            temperature=payload.get('temperature'))
                locally_handled = True

        # Always call the parent handler when done with local specific logic. This gives the opportunity to all
        # ancestors to catch all events.
        parent_handled = await super().async_handle_push_notification(namespace=namespace, data=data)
        return locally_handled or parent_handled

    async def async_handle_update(self, namespace: Namespace, data: dict) -> bool:
        _LOGGER.debug(f"Handling {self.__class__.__name__} mixin data update.")
        locally_handled = False
        if namespace == Namespace.SYSTEM_ALL:
            light_data = data.get('all', {}).get('digest', {}).get('light', [])
            self._update_channel_status(channel=light_data.get('channel'),
                                        rgb=light_data.get('rgb'),
                                        luminance=light_data.get('luminance'),
                                        temperature=light_data.get('temperature'),
                                        onoff=light_data.get('onoff'))
            locally_handled = True
        super_handled = await super().async_handle_update(namespace=namespace, data=data)
        return super_handled or locally_handled

    def _supports_mode(self, mode: LightMode, channel: int = 0) -> bool:
        capacity = self.abilities.get(Namespace.CONTROL_LIGHT.value, {}).get('capacity')
        if capacity is None:
            return False

        return (capacity & mode.value) == mode.value

    def _update_channel_status(self,
                               channel: int = 0,
                               rgb: Union[int, RgbTuple] = None,
                               luminance: int = -1,
                               temperature: int = -1,
                               onoff: int = None) -> None:
        channel_info = self._channel_light_status.get(channel)
        if channel_info is None:
            channel_info = LightInfo()
            self._channel_light_status[channel] = channel_info

        channel_info.update(rgb=rgb, luminance=luminance, temperature=temperature, onoff=onoff)

    async def async_set_light_color(self,
                                    channel: int = 0,
                                    onoff: Optional[bool] = None,
                                    rgb: Optional[RgbTuple] = None,
                                    luminance: Optional[int] = -1,
                                    temperature: Optional[int] = -1,
                                    skip_rate_limits: bool = False,
                                    drop_on_overquota: bool = True,
                                    *args,
                                    **kwargs) -> None:
        """
        Controls the light color of the given bulb. Please note that the __onoff parameter is ignored if the
        device supports Toggle or ToggleX operations__.

        :param channel: channel to control (for bulbs it's usually 0)
        :param onoff: when True, the device will be turned on, when false, it will turned off. This parameter is ignored
                      if the operating device must be controlled via ToggleX or Toggle command.
        :param rgb: (red,green,blue) tuple, where each color is an integer from 0-to-255
        :param luminance: Light intensity (at least on MSL120). Varies from 0 to 100
        :param temperature: Light temperature. Can be used when rgb is not specified.

        :return: None
        """
        if rgb is not None and temperature != -1:
            _LOGGER.error("You are trying to set both RGB and luminance values for this bulb. It won't work!")

        # Prepare a basic command payload
        payload = {
            'light': {
                'channel': channel,
                'gradual': 0
            }
        }

        # For some reason, not all the Meross Devices do offer 'onoff' control attribute. For instance, the
        # light of the smart humidifier does require this parameter to be set, while the MSL120 requires
        # Toggle/ToggleX usage. For this reason, we'll only set the onoff value when Toggle/ToggleX is unavailable.
        if onoff is not None:
            if isinstance(self, ToggleMixin) or isinstance(self, ToggleXMixin):
                _LOGGER.warning(f"Device {self.name} seems to support ToggleX/Toggle; Ignoring onoff parameter.")
            else:
                payload['light']['onoff'] = 1 if onoff else 0
        else:
            if self._channel_light_status[channel].is_on is not None:
                payload['light']['onoff'] = 1 if self._channel_light_status[channel].is_on else 0

        mode = 0
        if self._supports_mode(LightMode.MODE_RGB) and rgb is not None:
            # Convert the RGB to integer
            color = rgb_to_int(rgb)
            payload['light']['rgb'] = color
            mode = mode | LightMode.MODE_RGB.value

        if self._supports_mode(LightMode.MODE_LUMINANCE) and luminance != -1:
            payload['light']['luminance'] = luminance
            mode = mode | LightMode.MODE_LUMINANCE.value

        if self._supports_mode(LightMode.MODE_TEMPERATURE) and temperature != -1:
            payload['light']['temperature'] = temperature
            mode = mode | LightMode.MODE_TEMPERATURE.value

        payload['light']['capacity'] = mode

        await self._execute_command(method='SET',
                                    namespace=Namespace.CONTROL_LIGHT,
                                    payload=payload,
                                    skip_rate_limits=skip_rate_limits,
                                    drop_on_overquota=drop_on_overquota)

        # If the command was ok, immediately update the local state.
        self._update_channel_status(channel, rgb=rgb, luminance=luminance, temperature=temperature)

    def get_supports_rgb(self, channel: int = 0) -> bool:
        """
        Tells if the current device supports RGB capability

        :param channel: channel to get info from, defaults to 0

        :return: True if the current device supports RGB color, False otherwise.
        """
        return self._supports_mode(LightMode.MODE_RGB, channel=channel)

    def get_supports_luminance(self, channel: int = 0) -> bool:
        """
        Tells if the current device supports luminance capability

        :param channel: channel to get info from, defaults to 0

        :return: True if the current device supports luminance mode, False otherwise.
        """
        return self._supports_mode(LightMode.MODE_LUMINANCE, channel=channel)

    def get_supports_temperature(self, channel: int = 0) -> bool:
        """
        Tells if the current device supports temperature color capability

        :param channel: channel to get info from, defaults to 0

        :return: True if the current device supports temperature mode, False otherwise.
        """
        return self._supports_mode(LightMode.MODE_TEMPERATURE, channel=channel)

    def get_rgb_color(self, channel=0, *args, **kwargs) -> Optional[RgbTuple]:
        """
        Returns the current RGB configuration of the device.

        :param channel: channel to control, defaults to 0 (bulbs generally have only one channel)

        :return: a Tuple containing three integer 8bits values (red, green, blue)
        """
        self.check_full_update_done()
        info = self._channel_light_status.get(channel)
        if info is None:
            return None
        return info.rgb_tuple

    def get_luminance(self, channel=0, *args, **kwargs) -> Optional[int]:
        """
        Returns the current brightness intensity of the bulb

        :param channel: channel to control, defaults to 0 (bulbs generally have only one channel)

        :return: an integer value from 0 to 100
        """
        self.check_full_update_done()
        info = self._channel_light_status.get(channel)
        if info is None:
            return None
        return info.luminance

    def get_color_temperature(self, channel=0, *args, **kwargs) -> Optional[int]:
        """
        Returns the current color_temperature

        :param channel: channel to control, defaults to 0 (bulbs generally have only one channel)

        :return: an integer value from 0 to 100
        """
        self.check_full_update_done()
        info = self._channel_light_status.get(channel)
        if info is None:
            return None
        return info.temperature

    def get_light_is_on(self, channel=0, *args, **kwargs) -> Optional[bool]:
        """
        Returns True if the light is ON, False otherwise.

        :param channel: channel to control, defaults to 0 (bulbs generally have only one channel)

        :return: current onoff state
        """
        # For some reason, Meross devices that support ToggleX and Toggle abilities, do not expose onoff
        # state within light status. In that case, we return the channel status.
        self.check_full_update_done()
        if isinstance(self, ToggleXMixin) or isinstance(self, ToggleMixin):
            return self.is_on(channel=channel)

        info = self._channel_light_status.get(channel)
        if info is None:
            return None
        return info.is_on

    async def async_turn_on(self, channel=0, *args, **kwargs) -> None:
        if isinstance(self, ToggleXMixin) or isinstance(self, ToggleMixin):
            await super().async_turn_on(channel=channel, *args, **kwargs)
        else:
            await self.async_set_light_color(channel=channel, onoff=True)

    async def async_turn_off(self, channel=0, *args, **kwargs) -> None:
        if isinstance(self, ToggleXMixin) or isinstance(self, ToggleMixin):
            await super().async_turn_off(channel=channel, *args, **kwargs)
        else:
            await self.async_set_light_color(channel=channel, onoff=False)
