import logging


_LOGGER = logging.getLogger(__name__)


def extract_domain(address: str) -> str:
    tokens = address.split(":")
    return tokens[0]
