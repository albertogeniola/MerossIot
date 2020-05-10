import logging
from typing import Optional, Union

from meross_iot.model.enums import Namespace, LightMode
from meross_iot.model.plugin.light import LightInfo
from meross_iot.model.push.generic import GenericPushNotification
from meross_iot.model.typing import RgbTuple
from meross_iot.utilities.conversion import rgb_to_int

_LOGGER = logging.getLogger(__name__)


class LightMixin(object):
    _execute_command: callable
    _abilities_spec: dict
    handle_update: callable

    def __init__(self, device_uuid: str,
                 manager,
                 **kwargs):
        super().__init__(device_uuid=device_uuid, manager=manager, **kwargs)

        # Dictionary keeping the status for every channel
        self._channel_light_status = {}

    def handle_push_notification(self, push_notification: GenericPushNotification) -> bool:
        locally_handled = False

        if push_notification.namespace == Namespace.LIGHT:
            _LOGGER.debug(f"LightMixin handling push notification for namespace {push_notification.namespace}")
            payload = push_notification.raw_data.get('light')
            if payload is None:
                _LOGGER.error(f"LightMixin could not find 'light' attribute in push notification data: "
                              f"{push_notification.raw_data}")
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
        parent_handled = super().handle_push_notification(push_notification=push_notification)
        return locally_handled or parent_handled

    def handle_update(self, data: dict) -> None:
        _LOGGER.debug(f"Handling {self.__class__.__name__} mixin data update.")
        light_data = data.get('all', {}).get('digest', {}).get('light', [])
        self._update_channel_status(channel=light_data.get('channel'),
                                    rgb=light_data.get('rgb'),
                                    luminance=light_data.get('luminance'),
                                    temperature=light_data.get('temperature'))
        super().handle_update(data=data)

    def _supports_mode(self, mode: LightMode) -> bool:
        return (self._abilities_spec.get(Namespace.LIGHT.value).get('capacity') & mode.value) == mode.value

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
        :param channel: Channel to control (for bulbs it's usually 0)
        :param rgb: (red,green,blue) tuple, where each color is an integer from 0-to-255
        :param luminance: Light intensity (at least on MSL120). Varies from 0 to 100
        :param temperature: Light temperature. Can be used when rgb is not specified.
        :return:
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

        await self._execute_command(method='SET', namespace=Namespace.LIGHT, payload=payload)

        # If the command was ok, immediately update the local state.
        self._update_channel_status(channel, rgb=rgb, luminance=luminance, temperature=temperature)

    @property
    def supports_rgb(self) -> bool:
        return self._supports_mode(LightMode.MODE_RGB)

    @property
    def supports_luminance(self) -> bool:
        return self._supports_mode(LightMode.MODE_LUMINANCE)

    @property
    def supports_temperature(self) -> bool:
        return self._supports_mode(LightMode.MODE_TEMPERATURE)

    @property
    def rgb_color(self, channel=0, *args, **kwargs) -> Optional[RgbTuple]:
        info = self._channel_light_status.get(channel)
        if info is None:
            return None
        return info.rgb_tuple
