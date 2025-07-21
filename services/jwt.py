"""Utility functions for issuing and verifying JWTs."""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

from jose import JWTError, jwt

JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
SECRET_KEY = os.getenv("SECRET_KEY", "secret")
EXPIRATION_SECONDS = int(os.getenv("TOKEN_EXPIRATION_SECONDS", "7200"))
RSA_PRIVATE_KEY_PATH = os.getenv("RSA_PRIVATE_KEY_PATH")
RSA_PUBLIC_KEY_PATH = os.getenv("RSA_PUBLIC_KEY_PATH")

if JWT_ALGORITHM == "RS256":
    if not RSA_PRIVATE_KEY_PATH or not RSA_PUBLIC_KEY_PATH:
        raise RuntimeError(
            "RSA_PRIVATE_KEY_PATH and RSA_PUBLIC_KEY_PATH must be set for RS256"
        )
    with open(RSA_PRIVATE_KEY_PATH, "rb") as fh:
        PRIVATE_KEY = fh.read()
    with open(RSA_PUBLIC_KEY_PATH, "rb") as fh:
        PUBLIC_KEY = fh.read()
else:
    PRIVATE_KEY = SECRET_KEY
    PUBLIC_KEY = SECRET_KEY


def create_token(
    *,
    user_id: str,
    email: str,
    role: str,
    provider: str,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a signed JWT access token."""

    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(seconds=EXPIRATION_SECONDS))
    payload = {
        "sub": user_id,
        "email": email,
        "role": role,
        "provider": provider,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }
    return jwt.encode(payload, PRIVATE_KEY, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> Dict[str, Any]:
    """Decode a JWT and return its payload."""

    try:
        return jwt.decode(token, PUBLIC_KEY, algorithms=[JWT_ALGORITHM])
    except JWTError as exc:  # pragma: no cover
        raise ValueError("Invalid token") from exc
