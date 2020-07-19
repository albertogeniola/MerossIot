from meross_iot.http_api import ErrorCodes


class AuthenticatedPostException(Exception):
    pass


class HttpApiError(AuthenticatedPostException):
    def __init__(self, error_code: ErrorCodes):
        self._error_code = error_code

    @property
    def error_code(self):
        return self._error_code


class BadLoginException(Exception):
    pass


class UnauthorizedException(Exception):
    pass


class TokenExpiredException(Exception):
    pass


class TooManyTokensException(Exception):
    pass


