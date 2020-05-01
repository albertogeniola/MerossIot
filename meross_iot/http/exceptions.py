class AuthenticatedPostException(Exception):
    pass


class UnauthorizedException(Exception):
    pass


class TokenExpiredException(Exception):
    pass


class TooManyTokensException(Exception):
    pass
