class UnconnectedError(Exception):
    pass


class CommandTimeoutError(Exception):
    pass


class MqttError(Exception):
    def __init__(self, message=None):
        super().__init__()
        self._message = message


class CommandError(Exception):
    def __init__(self, error_payload: dict):
        super().__init__()
        self.error_payload = error_payload


class RateLimitExceeded(Exception):
    pass


class UnknownDeviceType(Exception):
    pass