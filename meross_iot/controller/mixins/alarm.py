"""
This module contains the Mixins related to alarms functionalities.
"""

import logging
from collections import deque
from typing import Any, Dict, Deque, List

from meross_iot.controller.device import BaseDevice
from meross_iot.model.enums import Namespace

_LOGGER = logging.getLogger(__name__)


class AlarmMixin(BaseDevice):
    """
    Handles the events and the functionalities related to the
    `Namespace.CONTROL_ALARM` namespace.
    """
    __last_alarm_events: List[Dict]

    def __init__(self, device_uuid: str,
                 manager,
                 **kwargs):
        super().__init__(device_uuid=device_uuid, manager=manager, **kwargs)
        self.__last_alarm_events = []

    # Note: we are not overriding async_handle_update, as it seems the SYSTEM_ALL update
    #  does not carry information about latest alarms.

    async def async_update(self,
                           *args,
                           **kwargs) -> None:
        """
        Forces a full data update on the device. If your network bandwidth is limited or if you are running
        this program on an embedded device, try to invoke this method only when strictly needed.
        Most of the parameters of a device are updated automatically upon push-notification received
        by the meross MQTT cloud.
        :return: None
        """
        # Let's call the super implementation first (bubbling up). This is useful
        # when we are nesting multiple mixins and need to handle an event at multiple levels
        await super().async_update()

        # Let's enrich the state update
        await self.alarm_refresh_last_event()

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
            self.__handle_alarm_data(data['alarm'])
            locally_handled = True

        # Always call the parent handler when done with local specific logic. This gives the opportunity to all
        # ancestors to catch all events.
        parent_handled = await super()._async_handle_push_notification(namespace=namespace, data=data)
        return locally_handled or parent_handled

    async def alarm_refresh_last_event(self) -> None:
        """
        Queries the HUB regarding the last alarm events
        :return:
        """
        data = await self._execute_command(method="GET", namespace=Namespace.CONTROL_ALARM, payload={'alarm': []})
        self.__handle_alarm_data(data['alarm'])

    @property
    def alarm_last_events(self) -> List[Dict]:
        """
        Returns the last events received from the device.
        :return:
        """
        return self.__last_alarm_events.copy()

    def __handle_alarm_data(self, data: List[Dict]) -> None:
        self.__last_alarm_events.clear()
        for evt in data:
            self.__last_alarm_events.append(evt['event'])