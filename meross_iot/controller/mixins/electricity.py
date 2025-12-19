import logging
from datetime import datetime
from typing import Optional

from meross_iot.controller.device import BaseDevice, ensure_full_update
from meross_iot.model.enums import Namespace
from meross_iot.model.plugin.power import PowerInfo

_LOGGER = logging.getLogger(__name__)

_DATE_FORMAT = '%Y-%m-%d'


class ElectricityMixin(BaseDevice):

    def __init__(self, device_uuid: str,
                 manager,
                 **kwargs):
        super().__init__(device_uuid=device_uuid, manager=manager, **kwargs)

        # We'll hold a dictionary of lastest samples, one per channel
        self.__electricity_cached_samples = {}

    async def async_update(self, *args, **kwargs) -> None:
        """
        Forces a full data update on the device.
        """
        # Let's call the super implementation first (bubbling up).
        await super().async_update(*args, **kwargs)

        # Let's enrich the state update
        await self.async_electricity_fetch_instant_metrics(*args, **kwargs)

    async def async_handle_update(self, namespace: Namespace, data: dict) -> bool:
        locally_handled = False
        if namespace == Namespace.SYSTEM_ALL:
            # It seems that electricity data is not part of SYSTEM_ALL,
            # so we might need to manually fetch it if we want to stay updated.
            # However, usually async_handle_update is about processing data *received*.
            # If SYSTEM_ALL doesn't have it, we don't extract it.
            pass

        super_handled = await super().async_handle_update(namespace=namespace, data=data)
        return super_handled or locally_handled

    # Note: we are not overriding _async_handle_push_notification, as it seems there
    # is no CONTROL_ELECTRICITY push notifications being dispatched.

    @ensure_full_update
    async def async_electricity_fetch_instant_metrics(self,
                                                      channel=0,
                                                      timeout: Optional[float] = None,
                                                      *args, **kwargs) -> PowerInfo:
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
                                             timeout=timeout)
        data = result['electricity']

        # For some reason, most of the Meross device report accurate instant power, but inaccurate voltage/current.
        current = float(data['current']) / 1000
        voltage = float(data['voltage']) / 10
        power = float(data['power']) / 1000

        result = PowerInfo(current_ampere=current, voltage_volts=voltage, power_watts=power,
                           sample_timestamp=datetime.utcnow())
        self.__electricity_cached_samples[channel] = result
        return result

    @ensure_full_update
    def electricity_get_last_sample(self, channel=0, *args, **kwargs) -> Optional[PowerInfo]:
        """
        Returns the previously cached value for the sensed power information (if any).

        :param channel: The channel to gather info from

        :return:
        """
        return self.__electricity_cached_samples.get(channel)
