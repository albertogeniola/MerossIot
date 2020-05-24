import logging

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

    async def async_get_instant_metrics(self, channel=0, *args, **kwargs) -> PowerInfo:
        """
        Returns the instant power consumption for this device. Please note that current/voltage combination may not
        be accurate as power is. So, refer to power attribute rather than calculate it as Voltage * Current.

        :param channel: channel where to read metrics from. Defaults to 0

        :return: a `PowerInfo` object describing the current measure data
        """
        result = await self._execute_command("GET", Namespace.CONTROL_ELECTRICITY, {'channel': channel})
        data = result.get('electricity')

        # For some reason, most of the Meross device report accurate instant power, but inaccurate voltage/current.
        current = float(data.get('current'))/1000
        voltage = float(data.get('voltage')) / 10
        power = float(data.get('power')) / 1000
        return PowerInfo(current_ampere=current, voltage_volts=voltage, power_watts=power)
