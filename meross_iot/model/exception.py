class UnconnectedError(Exception):
    pass


class CommandTimeoutError(Exception):
    pass


class CommandError(Exception):
    def __init__(self, error_payload: dict):
        super().__init__()
        self.error_payload = error_payload
