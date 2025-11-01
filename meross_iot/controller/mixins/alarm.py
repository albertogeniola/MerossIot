"""
This module contains the Mixins related to alarms functionalities.
"""

import logging
from collections import deque
from typing import Any, Dict, Deque

from meross_iot.controller.device import BaseDevice
from meross_iot.model.enums import Namespace

_LOGGER = logging.getLogger(__name__)

_MAX_ALARM_EVENTS_MEMORY = 10


class AlarmMixin(BaseDevice):
    """
    Handles the events and the functionalities related to the
    `Namespace.CONTROL_ALARM` namespace.
    """
    __last_alarm_events: Deque[Dict]

    def __init__(self, device_uuid: str,
                 manager,
                 **kwargs):
        super().__init__(device_uuid=device_uuid, manager=manager, **kwargs)
        self.__last_alarm_events = deque(maxlen=_MAX_ALARM_EVENTS_MEMORY)

    # Note: we are not overriding async_handle_update, as it seems the SYSTEM_ALL update
    #  does not carry information about latest alarms.

    async def _async_handle_push_notification(self, namespace: Namespace, data: Any) -> bool:
        """
        Handles push notification updates
        :param namespace: Push notification header
        :param data: Push notification data
        :return:
        """
        locally_handled = False
        if namespace == Namespace.CONTROL_ALARM:
            # Note: we are not storing the channel the alarm refers to.
            _LOGGER.debug("AlarmMixin handling push notification for namespace %s", str(namespace))
            self.__last_alarm_events.append(data['alarm'][0]['event']['interConn']['value'])
            locally_handled = True

        # Always call the parent handler when done with local specific logic. This gives the opportunity to all
        # ancestors to catch all events.
        parent_handled = await super()._async_handle_push_notification(namespace=namespace, data=data)
        return locally_handled or parent_handled

    @property
    def last_events(self) -> Deque[Dict]:
        """
        Returns the last events received from the device.
        :return:
        """
        return self.__last_alarm_events.copy()
