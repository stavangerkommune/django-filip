"""
Custom exceptions for django-filip connection handling.
"""


class FilipError(Exception):
    """Base exception for all django-filip errors."""

    pass


class WrongConnectionTypeError(FilipError, TypeError):
    """
    Raised when trying to use a client/method on a connection of the wrong type.

    Example: calling .upload() on an API connection.
    """

    pass


class AuthenticationError(FilipError):
    """Base class for authentication-related failures."""

    pass


class MissingCredentialsError(AuthenticationError):
    """Required credentials (key, password, client identity, etc.) are missing."""

    pass


class TokenFetchError(AuthenticationError):
    """Failed to obtain or refresh an access token (client credentials flow, etc.)."""

    pass


class RateLimitError(FilipError):
    """Raised when rate limit is exceeded and we cannot wait/retry anymore."""

    pass


class ConnectionInactiveError(FilipError):
    """Attempted to use an inactive connection."""

    pass


class InvalidConfigurationError(FilipError):
    """Configuration on the Connection model is invalid or inconsistent."""

    pass
