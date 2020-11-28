import logging
from datetime import datetime
from typing import Optional

from meross_iot.model.enums import Namespace
from meross_iot.model.plugin.power import PowerInfo

_LOGGER = logging.getLogger(__name__)


_DATE_FORMAT = '%Y-%m-%d'


class ElectricityMixin(object):
    _execute_command: callable

    def __init__(self, device_uuid: str,
                 manager,
                 **kwargs):
        super().__init__(device_uuid=device_uuid, manager=manager, **kwargs)

        # We'll hold a dictionary of lastest samples, one per channel
        self.__channel_cached_samples = {}

    async def async_get_instant_metrics(self, channel=0, skip_rate_limits: bool = False, drop_on_overquota: bool = True, *args, **kwargs) -> PowerInfo:
        """
        Polls the device to gather the instant power consumption for this device.
        Please note that current/voltage combination may not be accurate as power is.
        So, refer to power attribute rather than calculate it as Voltage * Current.
        Avoid flooding the device by calling this methods so often. Instead. you should rely on the cached value
        offered by get_last_sample(): if it's None or if the sample_timestamp of the offered value is not recent
        enough, then you should call this method to refresh it.

        :param channel: channel where to read metrics from. Defaults to 0

        :return: a `PowerInfo` object describing the current measure data
        """
        result = await self._execute_command(method="GET",
                                             namespace=Namespace.CONTROL_ELECTRICITY,
                                             payload={'channel': channel},
                                             skip_rate_limits=skip_rate_limits,
                                             drop_on_overquota=drop_on_overquota)
        data = result.get('electricity')

        # For some reason, most of the Meross device report accurate instant power, but inaccurate voltage/current.
        current = float(data.get('current'))/1000
        voltage = float(data.get('voltage')) / 10
        power = float(data.get('power')) / 1000

        result = PowerInfo(current_ampere=current, voltage_volts=voltage, power_watts=power, sample_timestamp=datetime.utcnow())
        self.__channel_cached_samples[channel] = result
        return result

    def get_last_sample(self, channel=0, *args, **kwargs) -> Optional[PowerInfo]:
        """
        Returns the previously cached value for the sensed power information (if any).

        :param channel: The channel to gather info from

        :return:
        """
        return self.__channel_cached_samples.get(channel)
