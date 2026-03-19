import logging
from typing import Optional, Any, Tuple

from meross_iot.model.enums import Namespace, OnlineStatus
from meross_iot.model.push.generic import GenericPushNotification

_LOGGER = logging.getLogger(__name__)


class DoorWindowPushNotification(GenericPushNotification):
    def __init__(self, originating_device_uuid: str, raw_data: dict):
        super().__init__(namespace=Namespace.HUB_SENSOR_DOORWINDOW,
                         originating_device_uuid=originating_device_uuid,
                         raw_data=raw_data)
        opening = raw_data.get('doorWindow')
        if len(opening) != 1:
            _LOGGER.error("Triggered event with #%d events. This library can only handle alarm with a single trigger. Please open a BUG and reporto this payload: %s", len(opening), str(raw_data))

        # We assume we'll always have at least 1 alarm event
        event = opening[0]
        self._sub_device_id = event.get("id")
        self._latest_opening = event.get("status")
        self._latest_sample_time = event.get("lmTime")
        self._synced_time = event.get("syncedTime")
        self._samples = event.get("sample")

    @property
    def syncedTime(self) -> Optional[Tuple[int, int]]:
        """
        Returns the last samples for water-leak.
        :return:
        """
        if self._synced_time is None:
            return None
        else:
            return self._synced_time

    @property
    def latestSampleTime(self) -> Optional[int]:
        """
        Returns the latest sample timestamp
        :return:
        """
        if self._latest_sample_time is None:
            return None
        else:
            return self._latest_sample_time

    @property
    def latestSampleIsOpened(self) -> Optional[int]:
        """
        Returns true if the last sampling was an opening, false otherwise
        :return:
        """
        if self._latest_opening is None:
            return None
        else:
            return self._latest_opening

    @property
    def subdevice_id(self) -> Optional[str]:
        """
        If this event refers to a sub-device, this property contains the sub-device ID.
        In all other cases, this is None.
        :return:
        """
        return self._sub_device_id
