class AuthenticatedPostException(Exception):
    pass


class HttpApiError(AuthenticatedPostException):
    def __init__(self, error_code):
        self._error_code = error_code

    @property
    def error_code(self):
        return self._error_code


class BadLoginException(Exception):
    pass

class MissingMFA(BadLoginException):
    pass

class WrongMFA(BadLoginException):
    pass

class BadDomainException(Exception):
    def __init__(self, msg: str, api_domain: str, mqtt_domain:str):
        super().__init__(msg)
        self.api_domain = api_domain
        self.mqtt_domain = mqtt_domain


class UnauthorizedException(Exception):
    pass


class TokenExpiredException(Exception):
    pass


class TooManyTokensException(Exception):
    pass


