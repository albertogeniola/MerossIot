from meross_iot import name
try:
    from importlib import metadata
    from importlib.metadata import PackageNotFoundError
except ImportError:
    from importlib_metadata import metadata
    from importlib_metadata import PackageNotFoundError


def current_version():
    try:
        return metadata.version(name)
    except PackageNotFoundError:
        return "0.0.0"
