import logging
from logging import StreamHandler
from sys import stdout

ROOT_MEROSS_LOGGER = logging.getLogger("meross")
MANAGER_LOGGER = ROOT_MEROSS_LOGGER.getChild("manager")
CONNECTION_MANAGER_LOGGER = ROOT_MEROSS_LOGGER.getChild("connection")
NETWORK_DATA = ROOT_MEROSS_LOGGER.getChild("network_data")
POWER_PLUGS_LOGGER = ROOT_MEROSS_LOGGER.getChild("power_plugs")
BULBS_LOGGER = ROOT_MEROSS_LOGGER.getChild("light_bulbs")
DEVICE_LOGGER = ROOT_MEROSS_LOGGER.getChild("generic_device")


h = StreamHandler(stream=stdout)
ROOT_MEROSS_LOGGER.addHandler(h)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
h.setFormatter(formatter)


# Call this module to adjust the verbosity of the stream output. By default, only INFO is written to STDOUT log.
def set_log_level(root=logging.DEBUG, connection=logging.INFO, network=logging.INFO):
    ROOT_MEROSS_LOGGER.setLevel(root)
    CONNECTION_MANAGER_LOGGER.setLevel(connection)
    NETWORK_DATA.setLevel(network)
