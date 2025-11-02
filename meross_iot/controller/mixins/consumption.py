"""
This module contains the Mixins related to alarms power consumption.
"""

import logging
from datetime import datetime
from typing import List, Dict, Any

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

    # Note: we are not overriding async_handle_update, as it seems the SYSTEM_ALL update
    #  does not carry information about daily power consumption.

    async def async_update(self, *args, **kwargs) -> None:
        """
        Forces a full data update on the device.
        """
        # Let's call the super implementation first (bubbling up).
        await super().async_update()

        # Let's enrich the state update
        await self.async_consumption_fetch_summary()

    # Note: we are not overriding _async_handle_push_notification, as it seems there
    # is no CONSUMPTIONX or CONSUMPTION push notifications being dispatched.

    @property
    def consumption_daily_summary(self) -> List[Dict]:
        """
        Returns the daily power consumption data
        :return:
        """
        self.check_full_update_done()
        return self.__consumption_x.copy()

    async def async_consumption_fetch_summary(self,
                                              channel=0,
                                              timeout: float | None = None,
                                              *args, **kwargs) -> List[Dict]:
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
        self.__handle_consumption_data(data)
        return self.consumption_daily_summary

    def __handle_consumption_data(self, data: List[Dict]) -> None:
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
