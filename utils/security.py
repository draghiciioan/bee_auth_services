from __future__ import annotations

import warnings
from passlib.hash import bcrypt
from starlette.middleware.base import (
    BaseHTTPMiddleware,
    RequestResponseEndpoint,
)
from starlette.requests import Request
from starlette.types import ASGIApp


from .settings import settings

warnings.filterwarnings("ignore", "'crypt' is deprecated", DeprecationWarning)

# Configuration loaded from settings
SECRET_KEY = settings.secret_key
ALGORITHM = settings.jwt_algorithm
TOKEN_EXPIRATION_SECONDS = settings.token_expiration_seconds


def hash_password(password: str) -> str:
    """Hash a plain password using bcrypt."""
    return bcrypt.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    """Verify a password against its bcrypt hash."""
    return bcrypt.verify(password, hashed_password)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security-related HTTP headers to each response."""

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ):
        response = await call_next(request)
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault(
            "Content-Security-Policy",
            "frame-ancestors 'none'; default-src 'self';",
        )
        return response


