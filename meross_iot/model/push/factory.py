import logging
from typing import Optional

from meross_iot.model.enums import Namespace
from meross_iot.model.push.bind import BindPushNotification
from meross_iot.model.push.generic import GenericPushNotification
from meross_iot.model.push.online import OnlinePushNotification
from meross_iot.model.push.unbind import UnbindPushNotification

_LOGGER = logging.getLogger(__name__)


_PUSH_CLASSES = {
    Namespace.ONLINE: OnlinePushNotification,
    Namespace.BIND: BindPushNotification,
    Namespace.UNBIND: UnbindPushNotification
}


def push_notification_parser(namespace: Namespace, message_payload: dict) -> Optional[GenericPushNotification]:
    """
    Parses a typed version of a push notification messages given its dict representation as pushed by the
    meross cloud.
    :param namespace:
    :param message_payload:
    :return:
    """
    _LOGGER.debug(f"Parsing push notification {namespace}, payload: {message_payload}")
    target_class = _PUSH_CLASSES.get(namespace)

    if target_class is None:
        _LOGGER.error(f"The current implementation of the library is unable to handle events "
                      f"belonging to namespace {namespace.name}")
        return None

    event = None
    # Due to the change that Meross might perform on their side, we expect parsing validation errors when new
    # unknown push notification are detected.
    try:
        event = target_class.from_dict(message_payload)
        _LOGGER.debug(f"Parsing succeeded. Parsed Event: {event}")
    except:
        _LOGGER.error(f"Failed to parse push notification: {event}")
        return None

    return event
