import logging
from datetime import datetime
from typing import List

from meross_iot.model.enums import Namespace

_LOGGER = logging.getLogger(__name__)


_DATE_FORMAT = '%Y-%m-%d'


class ConsumptionXMixin(object):
    _execute_command: callable

    def __init__(self, device_uuid: str,
                 manager,
                 **kwargs):
        super().__init__(device_uuid=device_uuid, manager=manager, **kwargs)

    async def async_get_daily_power_consumption(self, channel=0, *args, **kwargs) -> List[dict]:
        """
        Returns the power consumption registered by this device.

        :param channel: channel to read data from

        :return: the historical consumption data
        """
        # TODO: returning a nice PowerConsumtpionReport object rather than a list of dict?
        result = await self._execute_command("GET", Namespace.CONTROL_CONSUMPTIONX, {'channel': channel})
        data = result.get('consumptionx')

        # Parse the json data into nice-python native objects
        res = [{
                'date': datetime.strptime(x.get('date'), _DATE_FORMAT),
                'total_consumption_kwh': float(x.get('value'))/1000
        } for x in data]

        return res
