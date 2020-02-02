def to_rgb(rgb):
    if rgb is None:
        return None
    elif isinstance(rgb, int):
        return rgb
    elif isinstance(rgb, tuple):
        red, green, blue = rgb
    elif isinstance(rgb, dict):
        red = rgb['red']
        green = rgb['green']
        blue = rgb['blue']
    else:
        raise Exception("Invalid value for RGB!")

    r = red << 16
    g = green << 8
    b = blue

    return r+g+b


def int_to_rgb(rgb):
    red = (rgb & 16711680) >> 16
    green = (rgb & 65280) >> 8
    blue = (rgb & 255)
    return red, green, blue