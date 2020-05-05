from typing import Optional

from meross_iot.model.enums import Namespace


class ToggleXMixin(object):
    def __init__(self):
        self._toggle_x_status = None

    @property
    def is_on(self) -> Optional[bool]:
        # TODO
        pass

    async def turn_off(self, channel=0):
        await self._execute_command("SET", Namespace.TOGGLEX, {'togglex': {"onoff": 0, "channel": channel}})

    async def turn_on(self, channel=0):
        await self._execute_command("SET", Namespace.TOGGLEX, {'togglex': {"onoff": 1, "channel": channel}})

    async def toggle(self, channel=0):
        # TODO
        pass
