from typing import Union, Optional, Tuple

from meross_iot.model.typing import RgbTuple
from meross_iot.utilities.conversion import int_to_rgb, rgb_to_int


class LightInfo(object):
    def __init__(self,
                 rgb: Union[int, Tuple[int, int, int]] = None,
                 luminance: int = None,
                 temperature: int = None,
                 capacity: int = None,
                 onoff: int = None):
        self._rgb = self._convert_rgb(rgb)
        self._luminance = luminance
        self._temperature = temperature
        self._capacity = capacity
        self._onoff = onoff

    @property
    def rgb_tuple(self) -> Optional[Tuple[int, int, int]]:
        return self._rgb

    @property
    def rgb_int(self) -> Optional[int]:
        if self._rgb is not None:
            return rgb_to_int(self._rgb)
        return None

    @property
    def luminance(self) -> Optional[int]:
        return self._luminance

    @property
    def temperature(self) -> Optional[int]:
        return self._temperature

    @property
    def is_on(self) -> Optional[bool]:
        if self._onoff is not None:
            return self._onoff == 1
        return None

    def update(self,
               rgb: Union[int, RgbTuple] = None,
               luminance: int = None,
               temperature: int = None,
               capacity: int = None,
               onoff: int = None,
               *args,
               **kwargs):
        if rgb is not None:
            self._rgb = self._convert_rgb(rgb)
        if luminance is not None:
            self._luminance = luminance
        if temperature is not None:
            self._temperature = temperature
        if capacity is not None:
            self._capacity = capacity
        if onoff is not None:
            self._onoff = onoff

    @staticmethod
    def _convert_rgb(rgb: Union[int, tuple]):
        if rgb is None:
            return None

        if isinstance(rgb, int):
            return int_to_rgb(rgb)
        elif isinstance(rgb, tuple):
            return rgb
        else:
            raise ValueError("rgb value must be either an integer or a (red, green. blue) integers (0-255) tuple.")
