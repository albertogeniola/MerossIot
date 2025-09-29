import logging
from typing import Optional, List
from collections import deque
from meross_iot.model.enums import Namespace

_LOGGER = logging.getLogger(__name__)

_MAX_ALARM_EVENTS_MEMORY = 10

class AlarmMixin(object):
    _execute_command: callable
    __last_alarm_events: deque

    def __init__(self, device_uuid: str,
                 manager,
                 **kwargs):
        super().__init__(device_uuid=device_uuid, manager=manager, **kwargs)
        self.__last_alarm_events = deque(maxlen=_MAX_ALARM_EVENTS_MEMORY)

    # Note: we are not hooking async_handle_update, as it seems the SYSTEM_ALL update
    #  does not carry information about latest alarms.

    async def async_handle_push_notification(self, namespace: Namespace, data: dict) -> bool:
        locally_handled = False
        if namespace == Namespace.CONTROL_ALARM:
            _LOGGER.debug(f"AlarmMixin handling push notification for namespace {namespace}")
            payload = data.get('alarm')
            if payload is None:
                _LOGGER.error(f"AlarmMixin could not find 'alarm' attribute in push notification data: {data}")
                locally_handled = False
            else:
                for alarm_event in payload:
                    self.__last_alarm_events.append(alarm_event)

                locally_handled = True

        # Always call the parent handler when done with local specific logic. This gives the opportunity to all
        # ancestors to catch all events.
        parent_handled = await super().async_handle_push_notification(namespace=namespace, data=data)
        return locally_handled or parent_handled

    @property
    def last_events(self):
        return self.__last_alarm_events.copy()