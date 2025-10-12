import logging
from typing import Optional, Dict, Any

from meross_iot.controller.device import GenericSubDevice
from meross_iot.model.enums import Namespace, OnlineStatus

_LOGGER = logging.getLogger(__name__)


class HubOnlineMixin(GenericSubDevice):
    """
    Mixin handling the online event for subdevices
    """

    def __init__(self, hubdevice_uuid: str, subdevice_id: str, status: int, last_active_time: int, manager):
        super().__init__(hubdevice_uuid=hubdevice_uuid, subdevice_id=subdevice_id, status=status,
                         last_active_time=last_active_time, manager=manager)
        # We don't create a dedicated __online attribute at this level, instead we rely on the
        #  base _online attribute from super-classes.

    async def async_update(self,
                           timeout: Optional[float] = None,
                           *args,
                           **kwargs) -> None:
        # Let's call the super implementation first (bubbling up). This is useful
        # when we are nesting multiple mixins and need to handle an event at multiple levels
        await super().async_update()

        # Some Mixins handle the online state by themselves.
        # For instance MS100 and MTS100 handle the online data within their specific
        # commands like HUB_SENSOR_ALL and HUB_MTS100_ALL.
        # In such cases, we don't want to issue a dedicated ONLINE update, as the online status
        # will be handled by those mixins.
        if Namespace.HUB_SENSOR_ALL in self._abilities or Namespace.HUB_MTS100_ALL in self.abilities:
            _LOGGER.debug(f"Skipping handling ONLINE update within HubOnlineMixin: SubDevice {self.subdevice_id} "
                          f"already has mixins taking care of that.")
            return

        # If the device requires explicit online state update, let's trigger it here.
        result = await self._execute_command(method="GET",
                                             namespace=Namespace.HUB_ONLINE,
                                             payload={'online': [{'id': self.subdevice_id}]},
                                             timeout=timeout)

        online_data = result.get('online')
        if online_data is None:
            _LOGGER.error(f"Missing online key within result data: {result}.")
            return
        data = next(filter(lambda x: x['id'] == self.subdevice_id, online_data))
        if data is None:
            _LOGGER.error(
                f"Returned data is missing the SubDevice id we are looking for '{self.subdevice_id}'. Data: {data}.")
            return
        self._handle_online_state_update(data=data)

    async def async_notify_hub_update(self, data: Dict) -> None:
        await super().async_notify_hub_update(data=data)
        # TODO: shall we intercept any state here?
        pass

    async def _async_handle_push_notification(self, namespace: str, data: Any) -> bool:
        # Let's call the super implementation first (bubbling up). This is useful
        # when we are nesting multiple mixins and need to handle an event at multiple levels
        parent_handled = await super()._async_handle_push_notification(namespace=namespace, data=data)

        locally_handled = False
        if namespace == Namespace.HUB_ONLINE.value:
            self._handle_online_state_update(data=data)
            locally_handled = True

        return locally_handled or parent_handled

    def _handle_online_state_update(self, data: Dict) -> None:
        # Attention: this method handles online event data by updating state at base class level.
        status = data.get('status')
        if status is not None:
            online_status = OnlineStatus(status)
            self._online = online_status
        else:
            _LOGGER.warning("Missing status key in online state update.")

        last_active_time = data.get('lastActiveTime')
        if last_active_time is not None:
            self._last_active_time=last_active_time
        else:
            _LOGGER.warning("Missing lastActiveTime key in online state update.")

