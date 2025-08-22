from typing import List
from meross_iot.controller.device import ChannelInfo

class DynamicFilteringMixin(object):
    # Filter device based on user-provided input. We presently match on the ability and name, but
    # may provide additional parameters in kwargs.
    # Returns true if filter matches, false if not
    @staticmethod
    def filter(device_ability : str, device_name : str,**kwargs):
        return False
# Some devices (e.g. BBSolar lights) use multiple channels to represent a single logical entity, but don't indicate 
# that in the abilities. Therefore, we provide a special type of mixin, the "channelRemappingMixin", which will provide
# the relevant channelInfo for us. 
class ChannelRemappingMixin(DynamicFilteringMixin):
    def remap(self,channelInfo : List[ChannelInfo]) -> List[ChannelInfo]:
        return None
    
    # We rely on the MRO here, and override the _parse_channels function
    # of the baseDevice
    def _parse_channels(self,channel_data: List) -> List[ChannelInfo]:
        res = super()._parse_channels(channel_data)
        remapped = self.remap(res)
        if remapped != None:
            return remapped
        # Fall-through, return original
        return res