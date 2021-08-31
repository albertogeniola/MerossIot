import pkg_resources
from meross_iot import name


def current_version():
    return pkg_resources.get_distribution(name).version
