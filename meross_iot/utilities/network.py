import logging
from typing import Optional

_LOGGER = logging.getLogger(__name__)


def extract_domain(address: str) -> str:
    tokens = address.split(":")
    return tokens[0]

def extract_port(address: str, default: int) -> int:
    tokens = address.split(":")
    if len(tokens) > 1:
        return tokens[1]
    return default

