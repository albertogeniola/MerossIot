from typing import Union


def rgb_to_int(rgb: Union[tuple, dict, int]) -> int:
    if isinstance(rgb, int):
        return rgb
    elif isinstance(rgb, tuple):
        red, green, blue = rgb
    elif isinstance(rgb, dict):
        red = rgb['red']
        green = rgb['green']
        blue = rgb['blue']
    else:
        raise ValueError("Invalid value for RGB!")

    r = red << 16
    g = green << 8
    b = blue

    return r+g+b


def int_to_rgb(rgb: int) -> tuple:
    red = (rgb & 16711680) >> 16
    green = (rgb & 65280) >> 8
    blue = (rgb & 255)
    return red, green, blue


