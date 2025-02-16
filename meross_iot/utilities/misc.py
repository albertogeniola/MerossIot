from meross_iot import name
from importlib import metadata
from importlib.metadata import PackageNotFoundError


def current_version():
    try:
        return metadata.version(name)
    except PackageNotFoundError:
        return "0.0.0"
