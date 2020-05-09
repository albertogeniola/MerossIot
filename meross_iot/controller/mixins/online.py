import logging

from meross_iot.model.enums import Namespace, OnlineStatus
from meross_iot.model.push.generic import GenericPushNotification

_LOGGER = logging.getLogger(__name__)


class OnlineMixin(object):
    _abilities_spec: dict
    _online: OnlineStatus

    def __init__(self, device_uuid: str,
                 manager,
                 **kwargs):
        super().__init__(device_uuid=device_uuid, manager=manager, **kwargs)

    def handle_push_notification(self, push_notification: GenericPushNotification) -> bool:
        locally_handled = False

        if push_notification.namespace == Namespace.ONLINE:
            _LOGGER.debug(f"OnlineMixin handling push notification for namespace {push_notification.namespace}")
            payload = push_notification.raw_data.get('online')
            if payload is None:
                _LOGGER.error(f"OnlineMixin could not find 'online' attribute in push notification data: "
                              f"{push_notification.raw_data}")
                locally_handled = False
            else:
                online_data = payload.get("online")
                status = OnlineStatus(online_data.get("status"))
                self._online = status
                locally_handled = True

        # Always call the parent handler when done with local specific logic. This gives the opportunity to all
        # ancestors to catch all events.
        parent_handled = super().handle_push_notification(push_notification=push_notification)
        return locally_handled or parent_handled
