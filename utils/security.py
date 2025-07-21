from __future__ import annotations

import os
import warnings
from passlib.hash import bcrypt
from starlette.middleware.base import (
    BaseHTTPMiddleware,
    RequestResponseEndpoint,
)
from starlette.requests import Request
from starlette.types import ASGIApp


warnings.filterwarnings("ignore", "'crypt' is deprecated", DeprecationWarning)

# Configuration loaded from environment variables
SECRET_KEY = os.getenv("SECRET_KEY", "secret")
ALGORITHM = "HS256"
TOKEN_EXPIRATION_SECONDS = int(os.getenv("TOKEN_EXPIRATION_SECONDS", "7200"))


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


