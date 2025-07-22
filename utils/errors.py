from enum import Enum


class ErrorCode(str, Enum):
    """Standardized application error codes."""

    EMAIL_ALREADY_REGISTERED = "email_already_registered"
    INVALID_CREDENTIALS = "invalid_credentials"
    EMAIL_NOT_VERIFIED = "email_not_verified"
    UNSUPPORTED_PROVIDER = "unsupported_provider"
    OAUTH_AUTH_FAILED = "oauth_auth_failed"
    EMAIL_NOT_AVAILABLE = "email_not_available"
    INVALID_TOKEN = "invalid_token"
    USER_NOT_FOUND = "user_not_found"
