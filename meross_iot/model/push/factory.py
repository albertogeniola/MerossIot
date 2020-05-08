import logging
from typing import Optional, Union

from meross_iot.model.enums import Namespace, get_or_parse_namespace
from meross_iot.model.push.bind import BindPushNotification
from meross_iot.model.push.generic import GenericPushNotification
from meross_iot.model.push.online import OnlinePushNotification
from meross_iot.model.push.unbind import UnbindPushNotification

_LOGGER = logging.getLogger(__name__)


def parse_push_notification(namespace: Union[str, Namespace],
                            message_payload: dict,
                            originating_device_uuid: str,
                            ) -> Optional[GenericPushNotification]:
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
        # Check we have a push notification class associate to that namespace
        return GenericPushNotification(namespace=parsed_namespace, originating_device_uuid=originating_device_uuid,
                                       raw_data=message_payload)
    except ValueError:
        return None
