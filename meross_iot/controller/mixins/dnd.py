import logging
from typing import Optional, Dict

from meross_iot.model.enums import Namespace, RollerShutterState

_LOGGER = logging.getLogger(__name__)


class SystemDndMixin:
    _execute_command: callable
    check_full_update_done: callable

    async def async_handle_push_notification(self, namespace: Namespace, data: dict) -> bool:
        locally_handled = False

        # Always call the parent handler when done with local specific logic. This gives the opportunity to all
        # ancestors to catch all events.
        parent_handled = await super().async_handle_push_notification(namespace=namespace, data=data)
        return locally_handled or parent_handled

