from datetime import datetime


class BatteryInfo(object):
    def __init__(self, battery_charge: float, sample_ts: datetime):
        self._battery_charge = battery_charge
        self._sample_ts = sample_ts

    @property
    def remaining_charge(self) -> float:
        """
        Expresses the remaining battery charge in percentage

        :return:
        """
        return self._battery_charge

    @property
    def sampled_datetime(self) -> datetime:
        """
        When the battery info has been sampled (timestamp dependant on your current timezone)
        :return:
        """
        return self._sample_ts
