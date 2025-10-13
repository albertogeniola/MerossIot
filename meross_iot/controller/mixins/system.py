import logging
from typing import Optional

from meross_iot.model.enums import Namespace, OnlineStatus

_LOGGER = logging.getLogger(__name__)


class SystemAllMixin(object):
    _execute_command: callable
    #async_handle_update: Callable[[Namespace, dict], Awaitable]

    def __init__(self, device_uuid: str,
                 manager,
                 **kwargs):
        super().__init__(device_uuid=device_uuid, manager=manager, **kwargs)

    async def async_update(self, timeout: Optional[float] = None, *args, **kwargs) -> None:
        # The async_update implementation of SystemAllMixin is different from others
        # We first trigger the update, then we call the async_handle_update for this device,
        # so that all state is propagated and all the mixins have the opportunity to handle
        # it correctly.

        # Nevertheless, we always call the super implementation, so that the baseclass has the opportunity
        # to specialize the behaviour.
        await super().async_update(timeout=timeout, *args, **kwargs)

        # Let's now call the SYSTEM_ALL
        result = await self._execute_command(method="GET",
                                             namespace=Namespace.SYSTEM_ALL,
                                             payload={},
                                             timeout=timeout)

        # Once we have all the data in place, let's give each Mixin the opportunity to update
        # the internal state
        await self.async_handle_update(namespace=Namespace.SYSTEM_ALL, data=result)


class SystemOnlineMixin(object):
    _online: OnlineStatus
    #async_handle_update: Callable[[Namespace, dict], Awaitable]

    def __init__(self, device_uuid: str,
                 manager,
                 **kwargs):
        super().__init__(device_uuid=device_uuid, manager=manager, **kwargs)

    async def async_handle_update(self, namespace: Namespace, data: dict) -> bool:
        _LOGGER.debug(f"Handling {self.__class__.__name__} mixin data update.")
        locally_handled = False
        if namespace == Namespace.SYSTEM_ALL:
            online_data = data.get('all').get('system').get('online')
            status = OnlineStatus(int(online_data.get("status")))
            self._online = status
            locally_handled = True

        super_handled = await super().async_handle_update(namespace=namespace, data=data)
        return super_handled or locally_handled

    async def _async_handle_push_notification(self, namespace: str, data: dict) -> bool:
        locally_handled = False

        if namespace == Namespace.SYSTEM_ONLINE.value:
            _LOGGER.debug(f"OnlineMixin handling push notification for namespace {namespace}")
            payload = data.get('online')
            if payload is None:
                _LOGGER.error(f"OnlineMixin could not find 'online' attribute in push notification data: "
                              f"{data}")
                locally_handled = False
            else:
                status = OnlineStatus(int(payload.get("status")))
                self._online = status
                locally_handled = True

        # Always call the parent handler when done with local specific logic. This gives the opportunity to all
        # ancestors to catch all events.
        parent_handled = await super()._async_handle_push_notification(namespace=namespace, data=data)
        return locally_handled or parent_handled
