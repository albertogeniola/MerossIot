import logging
from typing import Optional, Union
from meross_iot.controller.mixins.utilities import ChannelRemappingMixin
from meross_iot.controller.mixins.toggle import ToggleXMixin
from meross_iot.controller.mixins.luminance import LuminanceMixin
from meross_iot.controller.mixins.light import LightMixin
from meross_iot.model.enums import Namespace, LightMode
from meross_iot.model.plugin.light import LightInfo
from meross_iot.model.typing import RgbTuple
from meross_iot.controller.device import ChannelInfo

_LOGGER = logging.getLogger(__name__)

class PlantLightMixin(ChannelRemappingMixin,LightMixin,ToggleXMixin,LuminanceMixin):
    """
    Mixin class that enables light control for BBSolar Smart Plant Lights.
    """
    _execute_command: callable
    check_full_update_done: callable

    WHITE_OFFSET = 0
    BLUE_OFFSET = 1
    RED_OFFSET = 2

    # async_handle_update: Callable[[Namespace, dict], Awaitable]

    def __init__(self, device_uuid: str,
                 manager,
                 **kwargs):
        super().__init__(device_uuid=device_uuid, manager=manager, **kwargs)

        # Dictionary keeping the status for every channel
        self._channel_light_status = {}
    
    @staticmethod
    def filter(device_ability, device_name,**kwargs):
        return device_name == 'bgl120a'

    def remap(self,channelInfo):
        return [
                ChannelInfo(index=0, name="Main Channel", channel_type=type, is_master_channel=True),
                ChannelInfo(index=1, name="Light A", channel_type=type, is_master_channel=False),
                ChannelInfo(index=2, name="Light B", channel_type=type, is_master_channel=False)
                ]
    
    def _update_main_channel(self):
        # Average out RGB and luminance values
        rgb = None
        luminance = None
        onOff = False
        
        for name,channel in self._channel_light_status.items():
            if name == 0:
                continue

            if rgb == None:
                rgb = channel.rgb_tuple
            elif channel.rgb_tuple != None:
                rgb = ((rgb[0] + channel.rgb_tuple[0]) / 2,
                       (rgb[1] + channel.rgb_tuple[1]) / 2,
                       (rgb[2] + channel.rgb_tuple[2]) / 2)
            if luminance == None:
                luminance = channel.luminance
            elif channel.luminance != None:
                luminance = (luminance + channel.luminance) / 2
            
            onOff = onOff or channel.is_on

        self._override_channel_status(0,luminance,rgb,onOff)

    def _override_channel_status(self,
                               channel: int = 0,
                               luminance : int = None,
                               rgb : RgbTuple = None,
                               onoff: int = None) -> None:
        channel_info = self._channel_light_status.get(channel)
        if channel_info is None:
            channel_info = LightInfo(luminance=0)
            self._channel_light_status[channel] = channel_info

        channel_info.update(rgb=rgb, luminance = luminance, onoff=onoff)
        # Nullify master channel since it's likely out of date
        if channel != 0:
            self._update_main_channel()
    
    def _calculate_scaling_factor(self,luminance):
        # We actually need to scale this twice - Once to get the 8-bit values for RGB into the 0-100 of luminance - This is easy, use a forced scaling factor of 2.55
        # then we need to scale by the luminance value
        if luminance != None:
            return (luminance / 100.0) / 2.55
        else:
            return 2.55
    
    def _update_channel_status(self,
                               channel: int = 0,
                               onoff: int = None) -> None:
        realChannel = (channel * 4) - 1
        channel_info = self._channel_light_status.get(channel)
        if channel_info is None:
            channel_info = LightInfo(luminance=0)
            self._channel_light_status[channel] = channel_info

        rgb = None
        luminance = self._channel_luminance_status.get(realChannel + self.WHITE_OFFSET,self._channel_light_status[channel].luminance)
        scalingFactor = self._calculate_scaling_factor(luminance)
        # We may not receive all updates right at the startup, so we need to check if the relevant channels exist. However,
        # the lights will always return the range of channels relevant to a single light
        if realChannel in self._channel_luminance_status:
            rgb = (self._channel_luminance_status[realChannel + self.RED_OFFSET]/scalingFactor,
                0,
                self._channel_luminance_status[realChannel + self.BLUE_OFFSET]/scalingFactor)
        channel_info.update(rgb=rgb, luminance = luminance, onoff=onoff)
        self._update_main_channel()
    
    async def async_handle_push_notification(self, namespace: Namespace, data: dict) -> bool:
        _LOGGER.debug(f"Handling {__name__} mixin push notification. Namespace: {namespace} Data: {data}")

        parent_handled = await LuminanceMixin.async_handle_push_notification(self,namespace=namespace, data=data)
        parent_handled2 = await ToggleXMixin.async_handle_push_notification(self,namespace=namespace, data=data) 
        # Update local cache - We do this in a really stupid way
        self._update_channel_status(1)
        self._update_channel_status(2)

        return parent_handled or parent_handled2

    async def async_handle_update(self, namespace: Namespace, data: dict) -> bool:
        _LOGGER.debug(f"Handling {self.__class__.__name__} mixin data update. Namespace: {namespace} Data: {data}")
        # Force the update order: we need to update the local state for the luminance and toggleX mixins, then can rely
        # on their labor
        if namespace == Namespace.CONTROL_LUMINANCE:
            await LuminanceMixin.async_handle_update(self,namespace,data)
        else:
            await ToggleXMixin.async_handle_update(self,namespace,data)

        # Update local cache - We do this in a really stupid way
        self._update_channel_status(1)
        self._update_channel_status(2)
                                    
        return True
    
    async def _async_request_update(self, timeout: Optional[float] = None, *args, **kwargs) -> None:
        await self.async_update_multiple_luminance_channels(range(3,11),timeout = 1)
        
    async def async_set_light_color(self,
                                    channel: int = 0,
                                    onoff: Optional[bool] = None,
                                    rgb: Optional[RgbTuple] = None,
                                    luminance: Optional[int] = None,
                                    temperature: Optional[int] = None,
                                    timeout: Optional[float] = None,
                                    *args,
                                    **kwargs) -> None:
        """
        Controls the light color of the given bulb. Please note that the __onoff parameter is ignored if the
        device supports Toggle or ToggleX operations__.

        :param channel: channel to control (for bulbs it's usually 0)
        :param onoff: when True, the device will be turned on, when false, it will turned off. This parameter is ignored
                      if the operating device must be controlled via ToggleX or Toggle command.
        :param rgb: (red,green,blue) tuple, where each color is an integer from 0-to-255. Note: we only use the red and blue channels here.
        :param luminance: Light intensity (at least on MSL120). Varies from 0 to 100
        :param temperature: Light temperature. Can be used when rgb is not specified.

        :return: None
        """
        # The main channel of these lights are effectively fake, and don't seem to do anything. Therefore, we manually drive channel 1 and 2
        if channel == 0:
            await self.async_set_light_color(1,onoff,rgb,luminance,timeout)
            await self.async_set_light_color(2,onoff,rgb,luminance,timeout)
            # Since this channel is fake anyway, we can update the status of it
            self._override_channel_status(0)
            return 
        # Handle turn-on/turn off cases - These smart lights only allow on/off for the main channels (e.g. light A and B)
        # they implement this via ToggleX
        if onoff != None:
            if channel > 2:
                _LOGGER.warning(f"Cannot perform on/off operation for indvidual LED's")
            else:
                if onoff == True:
                    await self.async_turn_on(channel, timeout=timeout)
                else:
                    await self.async_turn_off(channel, timeout=timeout)
        if channel <= 2:
            realChannel = (channel * 4) - 1

            # These lights don't seem to have a master luminance channel, we have to do it ourselves. However, the white channel is always
            # at 100%, so we use it as a point-of-reference. This is based on watching packet captures from the BBSolar app.
            if luminance is None:        
                # Get cached luminance value, use as reference
                luminance = self._channel_light_status[channel].luminance
                
            # If no RGB value has been selected, use the old one      
            if rgb is None:
                rgb = self._channel_light_status[channel].rgb_tuple
            
            scalingFactor = self._calculate_scaling_factor(luminance)

            rgbScaled = (int(rgb[0] * scalingFactor), int(rgb[1] * scalingFactor), int(rgb[2] * scalingFactor))

            # Send update
            await self.async_bulk_set_luminance({realChannel + self.WHITE_OFFSET: luminance, realChannel + self.RED_OFFSET: rgbScaled[0], realChannel + self.BLUE_OFFSET: rgbScaled[2]},timeout)
            self._override_channel_status(channel,luminance = luminance, rgb = rgb, onoff=onoff)
        else:
            _LOGGER.warning(f"Cannot set values for indvidual LED's")
        
    def get_supports_rgb(self, channel: int = 0) -> bool:
        """
        Tells if the current device supports RGB capability

        :param channel: channel to get info from, defaults to 0

        :return: True if the current device supports RGB color, False otherwise.
        """
        return True

    def get_supports_luminance(self, channel: int = 0) -> bool:
        """
        Tells if the current device supports luminance capability

        :param channel: channel to get info from, defaults to 0

        :return: True if the current device supports luminance mode, False otherwise.
        """
        return True

    def get_supports_temperature(self, channel: int = 0) -> bool:
        """
        Tells if the current device supports temperature color capability

        :param channel: channel to get info from, defaults to 0

        :return: True if the current device supports temperature mode, False otherwise.
        """
        return False