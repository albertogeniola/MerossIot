import pkg_resources

from meross_iot import name


def current_version():
    try:
        return pkg_resources.get_distribution(name).version
    except pkg_resources.DistributionNotFound:
        return "0.0.0"
