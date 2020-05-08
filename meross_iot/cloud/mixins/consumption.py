from typing import Optional, List

from meross_iot.model.enums import Namespace
from meross_iot.model.push.generic import GenericPushNotification
import logging
from datetime import datetime


_LOGGER = logging.getLogger(__name__)


_DATE_FORMAT = '%Y-%m-%d'


class ConsumptionXMixin(object):
    _execute_command: callable

    def __init__(self, device_uuid: str,
                 manager,
                 **kwargs):
        super().__init__(device_uuid=device_uuid, manager=manager, **kwargs)

    # TODO: handle push-notification for powerconsumptionx?

    async def async_get_daily_power_consumption(self, channel=0, *args, **kwargs) -> List[dict]:
        # TODO: returning a nice PowerConsumtpionReport object rather than a list of dict?
        result = await self._execute_command("GET", Namespace.CONSUMPTIONX, {})
        data = result.get('consumptionx')

        # Parse the json data into nice-python native objects
        res = [{
                'date': datetime.strptime(x.get('date'), _DATE_FORMAT),
                'total_consumption_kwh': float(x.get('value'))/1000
                # TODO: Time?
        } for x in data]

        return res
