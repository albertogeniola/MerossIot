import logging
from typing import Optional, Union

from meross_iot.model.enums import Namespace, get_or_parse_namespace
from meross_iot.model.push.bind import BindPushNotification
from meross_iot.model.push.generic import AbstractPushNotification
from meross_iot.model.push.online import OnlinePushNotification
from meross_iot.model.push.unbind import UnbindPushNotification

_LOGGER = logging.getLogger(__name__)


_PUSH_CLASSES = {
    Namespace.ONLINE: OnlinePushNotification,
    Namespace.BIND: BindPushNotification,
    Namespace.UNBIND: UnbindPushNotification
}


def parse_push_notification(namespace: Union[str, Namespace],
                            message_payload: dict,
                            originating_device_uuid: str,
                            ) -> Optional[AbstractPushNotification]:
    """
    Parses a typed version of a push notification messages given its dict representation as pushed by the
    meross cloud. If the parsing fails, it returns None. It's caller's responsibility to check the return
    value is not None.
    :param namespace:
    :param message_payload:
    :param originating_device_uuid:
    :return:
    """
    _LOGGER.debug(f"Parsing push notification {namespace}, payload: {message_payload}")

    # Parse the namespace
    try:
        parsed_namespace = get_or_parse_namespace(namespace)
    except ValueError:
        return None

    # Check we have a push notification class associate to that namespace
    target_class = _PUSH_CLASSES.get(parsed_namespace)
    if target_class is None:
        _LOGGER.error(f"The current implementation of the library is unable to handle events "
                      f"belonging to namespace {parsed_namespace.name}")
        return None

    # Parse and return the event
    # Due to the change that Meross might perform on their side, we expect parsing validation errors when new
    # unknown push notification are detected.
    event = None
    try:
        event = target_class.from_dict(message_payload, originating_device_uuid=originating_device_uuid)
        _LOGGER.debug(f"Parsing succeeded. Parsed Event: {event}")
    except:
        _LOGGER.error(f"Failed to parse push notification: {event}")
        return None

    return event
