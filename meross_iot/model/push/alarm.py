import logging
from typing import Optional, Any

from meross_iot.model.enums import Namespace, OnlineStatus
from meross_iot.model.push.generic import GenericPushNotification

_LOGGER = logging.getLogger(__name__)


class AlarmPushNotification(GenericPushNotification):
    def __init__(self, originating_device_uuid: str, raw_data: dict):
        super().__init__(namespace=Namespace.CONTROL_ALARM,
                         originating_device_uuid=originating_device_uuid,
                         raw_data=raw_data)
        alarm = raw_data.get('alarm')
        if len(alarm) != 1:
            _LOGGER.error("Triggered event with #%d events. This library can only handle alarm with a single trigger. Please open a BUG and reporto this payload: %s", len(alarm), str(raw_data))

        # We assume we'll always have at least 1 alarm event
        alarm_event = alarm[0]
        self._channel=alarm_event.get("channel")
        intercon=alarm_event.get("event").get("interConn")
        self._value = intercon.get("value")
        self._timestamp = intercon.get("timestamp")
        event_source = intercon.get("source")[0]
        self._sub_device_id = event_source.get("subId")

    @property
    def value(self) -> Optional[Any]:
        """
        Returns the alarm's value, if applicable
        :return:
        """
        return self._value

    @property
    def timestamp(self) -> Optional[int]:
        """
        Returns the alarm's timestamp, if applicable
        :return:
        """
        return self._timestamp

    @property
    def channel(self) -> Optional[int]:
        """
        Returns the device's channel, if applicable
        :return:
        """
        return self._channel

    @property
    def subdevice_id(self) -> Optional[str]:
        """
        If this event refers to a sub-device, this property contains the sub-device ID.
        In all other cases, this is None.
        :return:
        """
        return self._sub_device_id
