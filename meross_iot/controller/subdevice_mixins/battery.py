import logging
from datetime import datetime
from typing import Optional, Dict, List, Tuple

from meross_iot.controller.device import GenericSubDevice
from meross_iot.model.enums import Namespace

_LOGGER = logging.getLogger(__name__)


class BatteryMixin(GenericSubDevice):
    """
    Mixin class for implementing battery powered devices.
    """
    def __init__(self, hubdevice_uuid: str, subdevice_id: str, status: int, last_active_time: int, manager, **kwargs):
        super().__init__(hubdevice_uuid=hubdevice_uuid, subdevice_id=subdevice_id, status=status,
                         last_active_time=last_active_time, manager=manager, **kwargs)
        self.__battery: Optional[int] = None

    @property
    def battery_charge(self) -> Optional[int]:
        """
        Last cached info for battery state.
        :return: Battery charge percentage over 100
        """
        if self.__battery is None:
            return None
        return self.__battery

    async def async_update_battery_life(self,
                                     timeout: float | None = None,
                                     *args,
                                     **kwargs) -> int | None:
        """
        Polls the HUB/DEVICE to get its current battery status.
        :return:
        """
        data = await self._execute_command(method='GET',
                                                namespace=Namespace.HUB_BATTERY,
                                                payload={'battery': [{'id': self.subdevice_id}]},
                                                timeout=timeout)
        battery_dict = data.get('battery')
        if battery_dict is None:
            _LOGGER.error("Missing battery key from data update.")
        else:
            self._handle_battery_update(data=battery_dict)
        return self.battery_charge

    async def async_update(self,
                           timeout: float | None = None,
                           *args,
                           **kwargs) -> None:
        """
        Updates the state of the battery charge state.
        """
        # Let's call the super implementation first (bubbling up). This is useful
        # when we are nesting multiple mixins and need to handle an event at multiple levels
        await super().async_update(timeout=timeout)

        # Let's trigger a battery update command
        await self.async_update_battery_life(timeout=timeout)

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
        if 'battery' in data:
            self._handle_battery_update(data['battery'])
            locally_handled = True
        return super_handled or locally_handled

    async def _async_handle_push_notification(self, namespace: Namespace, data: dict) -> bool:
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
        if namespace == Namespace.HUB_BATTERY:
            self._handle_battery_update(data=data)
            locally_handled = True

        return locally_handled or parent_handled

    def _handle_battery_update(self, data: Dict):
        """
        Handles the HUB_BATTERY data payload.
        :param data: HUB_BATTERY data payload
        :return:
        """
        if 'value' not in data:
            _LOGGER.warning("Missing value keyword in battery state update.")
        else:
            self.__battery = data.get('value') # Only update the current status if the timestamp associated to the event is the latest
