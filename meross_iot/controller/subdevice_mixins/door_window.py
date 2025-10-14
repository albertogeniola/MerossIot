import logging
from datetime import datetime
from typing import Optional, Dict, List, Tuple

from meross_iot.controller.device import GenericSubDevice
from meross_iot.model.enums import Namespace

_LOGGER = logging.getLogger(__name__)


class DoorWindowSensorMixin(GenericSubDevice):
    """
    Mixin class that provides support for door/window sensors (MS200).
    """
    def __init__(self, hubdevice_uuid: str, subdevice_id: str, status: int, last_active_time: int, manager):
        super().__init__(hubdevice_uuid=hubdevice_uuid, subdevice_id=subdevice_id, status=status,
                         last_active_time=last_active_time, manager=manager)
        self.__doorwindow_state: Optional[int] = None
        self.__doorwindow_state_timestamp: Optional[int] = -1
        self.__doorwindow_samples: List = []

    @property
    def door_window_opened(self) -> Optional[bool]:
        """
        Last door-window opened status.
        :return: True if the door is open, False otherwise
        """
        if self.__doorwindow_state is None:
            return None
        return self.__doorwindow_state == 1

    @property
    def door_window_state_timestamp(self) -> Optional[datetime]:
        """
        UTC datetime when the latest door window state is registered

        :return: latest sampling time in UTC, if available
        """
        if self.__doorwindow_state_timestamp is None:
            return None
        return datetime.fromtimestamp(self.__doorwindow_state_timestamp)

    @property
    def door_window_samples(self) -> List[Tuple[bool, datetime]]:
        """
        Returns a list of latest samples of the door-window status.
        Each sample contains a boolean (True=Open, False=Closed) and an associated
        UTC timestamp
        """
        return [(s[0] == 1, datetime.fromtimestamp(s[1])) for s in self.__doorwindow_samples]

    async def async_update(self,
                           timeout: Optional[float] = None,
                           *args,
                           **kwargs) -> None:
        """
        Updates the state of the door/window sensor by fetching the latest status from the hub.
        Calling this method on the SubDevice class, will only trigger data-fetching for the specific
        device. Call the async_update() method at hub level if you want to update all SubDevices
        states at the same time.
        """
        # Let's call the super implementation first (bubbling up). This is useful
        # when we are nesting multiple mixins and need to handle an event at multiple levels
        await super().async_update()

        # To update entirely the state of this device, we just need to trigger the MTS100_ALL command.
        result = await self._execute_command(method="GET",
                                             namespace=Namespace.HUB_SENSOR_DOORWINDOW,
                                             payload={'doorWindow': [{'id': self.subdevice_id}]},
                                             timeout=timeout)

        # Retrieve the sub-device specific data and update the status
        found = False
        subdevices_states = result.get('doorWindow')
        if not isinstance(subdevices_states, List):
            _LOGGER.error(
                f"Failed to get MTS100 data for subdevice {self.subdevice_id}. Returned command result is not a list.")
            return

        for subdev_state in subdevices_states:
            subdev_id = subdev_state.get('id')
            if subdev_id != self.subdevice_id:
                continue
            found = True
            self._handle_doorwindow_update(data=subdev_state)
            break

        if not found:
            _LOGGER.error(f"Failed to get MTS100 data for subdevice {self.subdevice_id}.")

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
        if 'doorWindow' in data:
            self._handle_doorwindow_update(data['doorWindow'])
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
        if namespace == Namespace.HUB_SENSOR_DOORWINDOW.value:
            self._handle_doorwindow_update(data=data)
            locally_handled = True

        return locally_handled or parent_handled

    def _handle_doorwindow_update(self, data: Dict):
        """
        Handles the HUB_SENSOR_DOORWINDOW data payload.
        :param data: HUB_SENSOR_DOORWINDOW data payload
        :return:
        """
        if 'status' not in data:
            _LOGGER.warning("Missing status keyword in doorwindow state update.")
        else:
            # Only update the current status if the timestamp associated to the event is the latest
            event_sample_timestamp = data.get('lmTime')
            if event_sample_timestamp is None:
                _LOGGER.debug(
                    "Missing lmTime in doorwindow state update, assuming this is the most recent update available")
                self.__doorwindow_state = data.get('status')
                self.__doorwindow_state_timestamp = int(datetime.utcnow().timestamp())
            else:
                if event_sample_timestamp > self.__doorwindow_state_timestamp:
                    self.__doorwindow_state = data.get('status')
                    self.__doorwindow_state_timestamp = int(datetime.utcnow().timestamp())
                else:
                    _LOGGER.debug(
                        "Skipping update for DoorWindow sensor as the received stample has an older timestamp")

        if 'sample' in data:
            self.__doorwindow_samples = data.get('sample', [])
