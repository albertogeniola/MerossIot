from enum import Enum

from meross_iot.cloud.abilities import HUB_MTS100_ALL, HUB_MTS100_TEMPERATURE, HUB_MTS100_MODE, HUB_TOGGLEX, \
    HUB_MTS100_ONLINE
from meross_iot.cloud.devices.subdevices.generic import GenericSubDevice
from meross_iot.logger import VALVES_LOGGER as l


class ThermostatMode(Enum):
    COMFORT = 1
    CUSTOM = 0
    ECONOMY = 2
    SCHEDULE = 3


class ThermostatV3Mode(Enum):
    AUTO = 3
    COOL = 2
    CUSTOM = 0
    ECONOMY = 4
    HEAT = 1


class ValveSubDevice(GenericSubDevice):

    def __init__(self, cloud_client, subdevice_id, parent_hub, **kwords):
        super().__init__(cloud_client, subdevice_id, parent_hub, **kwords)

    def _handle_push_notification(self, namespace, payload, from_myself=False):
        if namespace == HUB_MTS100_ALL:
            self._state.update(payload)
        elif namespace == HUB_TOGGLEX:
            self._state.get('togglex').update(payload)
        elif namespace == HUB_MTS100_MODE:
            self._state.get('mode').update(payload)
        elif namespace == HUB_MTS100_TEMPERATURE:
            self._state.get('temperature').update(payload)
        elif namespace == HUB_MTS100_ONLINE:  # TODO: check if this really exists
            self._state.get('online').update(payload)
        # TODO: handle TIME SYNC event
        # elif namespace == HUB_TIME_SYNC:
        #    self._state.get('togglex').update(payload)
        else:
            l.warn("Unsupported/unhandled event: %s" % namespace)

        # TODO: fire events.

    def __str__(self):
        return "{}".format(self._state)
