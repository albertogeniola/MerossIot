"""
This module contains the Mixins related to diffuser spray functionalities.
"""

import logging
from typing import Optional, Dict

from meross_iot.controller.device import BaseDevice, ensure_full_update
from meross_iot.model.enums import Namespace, DiffuserSprayMode


_LOGGER = logging.getLogger(__name__)


class DiffuserSprayMixin(BaseDevice):
    """
    Handles the capabilities offered by `Namespace.DIFFUSER_SPRAY` namespace.
    """

    def __init__(self, device_uuid: str,
                 manager,
                 **kwargs):
        super().__init__(device_uuid=device_uuid, manager=manager, **kwargs)

        # Dictionary keeping the status for every channel
        self.__diffuser_spray_status_by_channel: Dict[int, Dict] = {}

    # We don't override async_update, as the SYSTEM_ALL data brings all the necessary
    # info this mixin needs.

    async def _async_handle_push_notification(self, namespace: Namespace, data: dict) -> bool:
        locally_handled = False

        if namespace == Namespace.DIFFUSER_SPRAY:
            _LOGGER.debug(f"{self.__class__.__name__} handling push notification for namespace {namespace}")
            payload = data['spray']
            # Update the status of every channel that has been reported in this push
            # notification.
            for c in payload:
                channel = c['channel']
                self.__diffuser_spray_status_by_channel[channel] = c

            locally_handled = True

        # Always call the parent handler when done with local specific logic. This gives the opportunity to all
        # ancestors to catch all events.
        parent_handled = await super()._async_handle_push_notification(namespace=namespace, data=data)
        return locally_handled or parent_handled

    async def async_handle_update(self, namespace: Namespace, data: dict) -> bool:
        _LOGGER.debug(f"Handling {self.__class__.__name__} mixin data update.")
        locally_handled = False
        if namespace == Namespace.SYSTEM_ALL:
            diffuser_data = data.get('all', {}).get('digest', {}).get('diffuser', {}).get('spray', [])
            for l in diffuser_data:
                channel = l['channel']
                self.__diffuser_spray_status_by_channel[channel] = l
            locally_handled = True

        super_handled = await super().async_handle_update(namespace=namespace, data=data)
        return super_handled or locally_handled

    @ensure_full_update
    def diffuser_spray_get_mode(self, channel: int = 0, *args, **kwargs) -> DiffuserSprayMode:
        """
        Returns the current spray mode
        :param channel: channel to fetch info from
        :param args:
        :param kwargs:
        :return:
        """
        if channel not in self.__diffuser_spray_status_by_channel:
            raise ValueError("Invalid or unsupported channel specified")
        mode = self.__diffuser_spray_status_by_channel[channel]['mode']
        return DiffuserSprayMode(mode)

    @ensure_full_update
    async def async_diffuser_spray_set_mode(self, mode: DiffuserSprayMode, channel: int = 0, timeout: Optional[float] = None, *args, **kwargs) -> None:
        """
        Changes the operating mode for this device
        :param mode: mode to set
        :param channel: channel to handle
        :param timeout: command timeout
        :return:
        """
        if channel not in self.__diffuser_spray_status_by_channel:
            raise ValueError("Invalid or unsupported channel specified")

        spray_payload = {"mode": mode.value, "channel": channel}
        payload = {'spray': [spray_payload]}
        await self._execute_command(method='SET',
                                    namespace=Namespace.DIFFUSER_SPRAY,
                                    payload=payload,
                                    timeout=timeout)
        # Immediately update local state
        self.__diffuser_spray_status_by_channel[channel].update(spray_payload)
