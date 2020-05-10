import logging
from typing import Optional, Union

from meross_iot.model.enums import Namespace, get_or_parse_namespace
from meross_iot.model.push.bind import BindPushNotification
from meross_iot.model.push.generic import GenericPushNotification
from meross_iot.model.push.unbind import UnbindPushNotification

_LOGGER = logging.getLogger(__name__)


def parse_push_notification(namespace: Union[str, Namespace],
                            message_payload: dict,
                            originating_device_uuid: str,
                            ) -> Optional[GenericPushNotification]:
    """
    Parse the push notification and return the most appropriate handling class.
    The current implementation is able to discriminate Bind/Unbind specific push notification. All the
    others are returned as a GenericPushNotification.
    :param namespace:
    :param message_payload:
    :param originating_device_uuid:
    :return:
    """
    _LOGGER.debug(f"Parsing push notification {namespace}, payload: {message_payload}")

    # Parse the namespace
    try:
        parsed_namespace = get_or_parse_namespace(namespace)

        if parsed_namespace == Namespace.CONTROL_BIND:
            return BindPushNotification.from_dict(data=message_payload,
                                                  originating_device_uuid=originating_device_uuid)
        elif parsed_namespace == Namespace.CONTROL_UNBIND:
            return UnbindPushNotification.from_dict(data=message_payload,
                                                    originating_device_uuid=originating_device_uuid)
        return GenericPushNotification(namespace=parsed_namespace, originating_device_uuid=originating_device_uuid,
                                       raw_data=message_payload)
    except ValueError:
        return None
