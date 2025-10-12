import logging
from datetime import datetime
from typing import Optional, Iterable, Dict, List, Tuple

from meross_iot.controller.device import GenericSubDevice
from meross_iot.model.enums import Namespace, OnlineStatus, ThermostatV3Mode

_LOGGER = logging.getLogger(__name__)


class ToggleXSensorMixin(GenericSubDevice):

    def __init__(self, hubdevice_uuid:str, subdevice_id:str, status:int, last_active_time:int, manager):
        super().__init__(hubdevice_uuid=hubdevice_uuid, subdevice_id=subdevice_id, status=status, last_active_time=last_active_time, manager=manager)
        self.__state: Dict = {}

    @property
    def is_on(self) -> Optional[bool]:
        """
        The last open state of the sensor, as per last sampled ddata.
        :return:
        """
        onoff_state = self.__state.get('onoff')
        if onoff_state is None:
            return None
        else:
            return onoff_state == 1

    async def async_update(self,
                           timeout: Optional[float] = None,
                           *args,
                           **kwargs) -> None:
        # Let's call the super implementation first (bubbling up). This is useful
        # when we are nesting multiple mixins and need to handle an event at multiple levels
        await super().async_update()

        # To update entirely the state of this device, we just need to trigger the TOGGLEX command.
        result = await self._execute_command(method="GET",
                                                  namespace=Namespace.HUB_TOGGLEX,
                                                  payload={'togglex': [{'id': self.subdevice_id}]},
                                                  timeout=timeout)

        # Retrieve the sub-device specific data and update the status
        found = False
        subdevices_states = result.get('togglex')
        if not isinstance(subdevices_states, List):
            _LOGGER.error(f"Failed to get togglex data for subdevice {self.subdevice_id}. Returned command result is not a list.")
            return

        for subdev_state in subdevices_states:
            subdev_id = subdev_state.get('id')
            if subdev_id != self.subdevice_id:
                continue
            found = True
            await self._async_handle_togglex_update(data=subdev_state)
            break

        if not found:
            _LOGGER.error(f"Failed to get togglex data for subdevice {self.subdevice_id}.")

    async def async_notify_hub_update(self, data: Dict):
        await super().async_notify_hub_update(data=data)
        # TODO: shall we intercept any state here?
        pass

    async def _async_handle_push_notification(self, namespace: str, data: dict) -> bool:
        # Always call the parent handler when done with local specific logic. This gives the opportunity to all
        # ancestors to catch all events.
        parent_handled = await super()._async_handle_push_notification(namespace=namespace, data=data)

        locally_handled = False
        if namespace == Namespace.HUB_TOGGLEX.value:
            await self._async_handle_togglex_update(data=data)
            locally_handled = True

        return locally_handled or parent_handled

    async def _async_handle_togglex_update(self, data: Dict):
        """
        Updates the togglex state based on the payload received
        :param data:
        :return:
        """
        if 'onoff' not in data:
            _LOGGER.warning("Missing onoff key in data payload.")
        self.__state.update(data)
