"""
This module contains the Mixins related to alarms power consumption.
"""

import logging
from datetime import datetime
from typing import List, Dict

from meross_iot.controller.device import BaseDevice
from meross_iot.model.enums import Namespace

_LOGGER = logging.getLogger(__name__)

_DATE_FORMAT = '%Y-%m-%d'


class BaseConsumptionXMixin(BaseDevice):
    """
    Handles the capabilities offered by consumption namespaces
    """

    def __init__(self, device_uuid: str,
                 manager,
                 namespace: Namespace,
                 accessor: str,
                 **kwargs):
        super().__init__(device_uuid=device_uuid, manager=manager, **kwargs)
        self.__namespace = namespace
        self.__accessor = accessor
        self.__consumption_x: List[Dict] = []

    @property
    def daily_power_consumption(self) -> List[Dict[datetime, float]]:
        """
        Returns the daily power consumption data
        :return:
        """
        return self.__consumption_x.copy()

    async def async_update_daily_power_consumption(self,
                                                   channel=0,
                                                   timeout: float | None = None,
                                                   *args, **kwargs) -> List[Dict[datetime, float]]:
        """
        Returns the power consumption registered by this device.
        :param channel: channel to read data from
        :return: the historical consumption data
        """
        result: Dict = await self._execute_command(method="GET",
                                                   namespace=self.__namespace,
                                                   payload={'channel': channel},
                                                   timeout=timeout)

        data: List[Dict] = result[self.__accessor]
        self._handle_daily_power_consumption(data)
        return self.daily_power_consumption

    def _handle_daily_power_consumption(self, data: List[Dict]) -> None:
        self.__consumption_x = [{
            'date': datetime.strptime(x['date'], _DATE_FORMAT),
            'total_consumption_kwh': float(x['value']) / 1000
        } for x in data]


class ConsumptionXMixin(BaseConsumptionXMixin):
    """
    Handles the capabilities offered by `Namespace.CONTROL_CONSUMPTIONX` namespace.
    """

    def __init__(self, device_uuid: str,
                 manager,
                 **kwargs):
        super().__init__(device_uuid=device_uuid, manager=manager, namespace=Namespace.CONTROL_CONSUMPTIONX,
                         accessor="consumptionx", **kwargs)


class ConsumptionMixin(BaseConsumptionXMixin):
    """
    Handles the capabilities offered by `Namespace.CONTROL_CONSUMPTION` namespace.
    """

    def __init__(self, device_uuid: str,
                 manager,
                 **kwargs):
        super().__init__(device_uuid=device_uuid, manager=manager, namespace=Namespace.CONTROL_CONSUMPTION,
                         accessor="consumption", **kwargs)
