import logging
from logging import StreamHandler
from sys import stdout

MANAGER_LOGGER = logging.getLogger("connection_manager")
CONNECTION_MANAGER_LOGGER = logging.getLogger("connection_manager")
POWER_PLUGS_LOGGER = logging.getLogger("power_plugs")
BULBS_LOGGER = logging.getLogger("light_bulbs")
DEVICE_LOGGER = logging.getLogger("generic_device")

h = StreamHandler(stream=stdout)
h.setLevel(logging.DEBUG)

MANAGER_LOGGER.addHandler(h)
MANAGER_LOGGER.setLevel(logging.INFO)

CONNECTION_MANAGER_LOGGER.addHandler(h)
CONNECTION_MANAGER_LOGGER.setLevel(logging.INFO)

POWER_PLUGS_LOGGER.addHandler(h)
POWER_PLUGS_LOGGER.setLevel(logging.INFO)

BULBS_LOGGER.addHandler(h)
BULBS_LOGGER.setLevel(logging.INFO)

DEVICE_LOGGER.addHandler(h)
DEVICE_LOGGER.setLevel(logging.INFO)


# Call this module to adjust the verbosity of the stream output. By default, only INFO is written to STDOUT log.
def set_debug_level(level):
    logging.getLogger().setLevel(level)
