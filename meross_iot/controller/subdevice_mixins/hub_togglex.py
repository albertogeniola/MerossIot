import logging
from typing import Optional, Dict, List

from meross_iot.controller.device import GenericSubDevice
from meross_iot.model.enums import Namespace

_LOGGER = logging.getLogger(__name__)


class ToggleXSensorMixin(GenericSubDevice):
    """
    Mixin class that provides basic ON/OFF toggle features for HUB subdevices.
    """
    def __init__(self, hubdevice_uuid: str, subdevice_id: str, status: int, last_active_time: int, manager):
        super().__init__(hubdevice_uuid=hubdevice_uuid, subdevice_id=subdevice_id, status=status,
                         last_active_time=last_active_time, manager=manager)
        self.__onoff: Optional[int] = None

    @property
    def is_on(self) -> Optional[bool]:
        """
        The last state of the subdevice, as per last sampled data.
        :return: True if the device is ON, False otherwise.
        """
        if self.__onoff is None:
            return None
        return self.__onoff == 1

    async def async_turn_on(self, timeout: Optional[float] = None, *args, **kwargs) -> None:
        """
        Turns on the subdevice.
        :param timeout: command timeout
        """
        await self._execute_command(method='SET',
                                    namespace=Namespace.HUB_TOGGLEX,
                                    payload={'togglex': [{'id': self.subdevice_id, 'onoff': 1}]},
                                    timeout=timeout)
        self.__onoff = 1

    async def async_turn_off(self, timeout: Optional[float] = None, *args, **kwargs) -> None:
        """
        Turns off the subdevice.
        :param timeout: command timeout
        """
        await self._execute_command(method='SET',
                                    namespace=Namespace.HUB_TOGGLEX,
                                    payload={'togglex': [{'id': self.subdevice_id, 'onoff': 0}]},
                                    timeout=timeout)
        self.__onoff = 0

    async def async_update(self,
                           timeout: Optional[float] = None,
                           *args,
                           **kwargs) -> None:
        """
        Forces a full data update on the device.
        Calling this method on the SubDevice class, will only trigger data-fetching for the specific
        device. Call the async_update() method at hub level if you want to update all SubDevices
        states at the same time.
        """
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
            self._handle_togglex_update(data=subdev_state)
            break

        if not found:
            _LOGGER.error(f"Failed to get togglex data for subdevice {self.subdevice_id}.")

    async def async_notify_hub_update(self, data: Dict) -> bool:
        """
        This method is called by the HubMixin whenever a full update (SYSTEM_ALL) is received at hub-level.
        This allows the library to be more efficient: whenever you need to update the state of all SubDevices
        attached to a hub, just call the hub's async_update() and that will fetch and update the state of
        all related SubDevices.
        :param data: Contains the data as per SYSTEM_ALL digest key.
        :return: True if the state was handled, False otherwise
        """
        super_handled = await super().async_notify_hub_update(data=data)
        locally_handled = False
        #TODO: it seems togglex is not available as key for this events. We should check the onoff key instaead.
        if 'togglex' in data:
            self._handle_togglex_update(data=data)
            locally_handled = True
        return super_handled or locally_handled

    async def _async_handle_push_notification(self, namespace: str, data: dict) -> bool:
        """
        Handles SubDevice state update based on PushNotifications.
        Mixins can override this method in order to catch specific PushNotifications
        and update their internal state accordingly.
        :param namespace:
        :param data:
        :return:
        """
        # Always call the parent handler when done with local specific logic. This gives the opportunity to all
        # ancestors to catch all events.
        parent_handled = await super()._async_handle_push_notification(namespace=namespace, data=data)

        locally_handled = False
        if namespace == Namespace.HUB_TOGGLEX.value:
            self._handle_togglex_update(data=data)
            locally_handled = True

        return locally_handled or parent_handled

    def _handle_togglex_update(self, data: Dict):
        """
        Handles the HUB_TOGGLEX data payload.
        :param data: HUB_TOGGLEX data payload
        :return:
        """
        if 'onoff' in data:
            self.__onoff = data["onoff"]
        else:
            _LOGGER.warning("Missing onoff key in data payload.")
