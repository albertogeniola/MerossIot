class UnconnectedError(Exception):
    pass


class CommandTimeoutError(Exception):
    def __init__(self, message: str, target_device_uuid: str, timeout: float):
        self.message = message
        self.target_device_uuid = target_device_uuid
        self.timeout = timeout


class MqttError(Exception):
    def __init__(self, message=None):
        super().__init__()
        self._message = message


class CommandError(Exception):
    def __init__(self, error_payload: dict):
        super().__init__()
        self.error_payload = error_payload


class UnknownDeviceType(Exception):
    pass