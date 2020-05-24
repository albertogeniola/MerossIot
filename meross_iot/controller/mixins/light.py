import logging
from typing import Optional, Union

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
    _abilities_spec: dict
    handle_update: callable

    def __init__(self, device_uuid: str,
                 manager,
                 **kwargs):
        super().__init__(device_uuid=device_uuid, manager=manager, **kwargs)

        # Dictionary keeping the status for every channel
        self._channel_light_status = {}

    def handle_push_notification(self, namespace: Namespace, data: dict) -> bool:
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
        parent_handled = super().handle_push_notification(namespace=namespace, data=data)
        return locally_handled or parent_handled

    def handle_update(self, namespace: Namespace, data: dict) -> bool:
        _LOGGER.debug(f"Handling {self.__class__.__name__} mixin data update.")
        locally_handled = False
        if namespace == Namespace.SYSTEM_ALL:
            light_data = data.get('all', {}).get('digest', {}).get('light', [])
            self._update_channel_status(channel=light_data.get('channel'),
                                        rgb=light_data.get('rgb'),
                                        luminance=light_data.get('luminance'),
                                        temperature=light_data.get('temperature'))
            locally_handled = True
        super_handled = super().handle_update(namespace=namespace, data=data)
        return super_handled or locally_handled

    def _supports_mode(self, mode: LightMode, channel: int = 0) -> bool:
        capacity = self._abilities_spec.get(Namespace.CONTROL_LIGHT.value).get('capacity')
        return (capacity & mode.value) == mode.value

    def _update_channel_status(self,
                               channel: int = 0,
                               rgb: Union[int, RgbTuple] = None,
                               luminance: int = -1,
                               temperature: int = -1) -> None:
        channel_info = self._channel_light_status.get(channel)
        if channel_info is None:
            channel_info = LightInfo()
            self._channel_light_status[channel] = channel_info

        channel_info.update(rgb=rgb, luminance=luminance, temperature=temperature)

    async def async_set_light_color(self,
                                    channel: int = 0,
                                    rgb: RgbTuple = None,
                                    luminance: int = -1,
                                    temperature: int = -1,
                                    *args,
                                    **kwargs) -> None:
        """
        Controls the light color of the given bulb.

        :param channel: channel to control (for bulbs it's usually 0)
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

        await self._execute_command(method='SET', namespace=Namespace.CONTROL_LIGHT, payload=payload)

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
        info = self._channel_light_status.get(channel)
        if info is None:
            return None
        return info.rgb_tuple
