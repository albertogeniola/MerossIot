import logging
from typing import Optional, List, Any
from collections import deque
from meross_iot.model.enums import Namespace
from meross_iot.model.push.generic import GenericPushNotification

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

    async def _async_handle_push_notification(self, namespace:str, data:Any) -> bool:
        locally_handled = False
        if namespace == Namespace.CONTROL_ALARM.value:
            # Note: we are not storing the channel the alarm refers to.
            _LOGGER.debug(f"AlarmMixin handling push notification for namespace {namespace}")
            self.__last_alarm_events.append(data['alarm'][0]['event']['interConn']['value'])
            locally_handled = True

        # Always call the parent handler when done with local specific logic. This gives the opportunity to all
        # ancestors to catch all events.
        parent_handled = await super()._async_handle_push_notification(namespace=namespace, data=data)
        return locally_handled or parent_handled

    @property
    def last_events(self):
        return self.__last_alarm_events.copy()