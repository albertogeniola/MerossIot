from enum import Enum


class ClientStatus(Enum):
    INITIALIZED = 1
    CONNECTING = 2
    CONNECTED = 3
    SUBSCRIBED = 4
    CONNECTION_DROPPED = 5
