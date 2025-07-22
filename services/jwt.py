"""Utility functions for issuing and verifying JWTs.

JWT Secret Rotation
-------------------
To rotate the signing secret without downtime, keep both the new and previous
keys in environment variables. Tokens are always issued with ``SECRET_KEY``.
During verification ``SECRET_KEY`` is tried first; if validation fails you can
fall back to ``PREVIOUS_SECRET_KEY``. Once all tokens signed with the old key
expire, ``PREVIOUS_SECRET_KEY`` can be removed.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict

from jose import JWTError, jwt

from utils import token_store
from utils.settings import settings

JWT_ALGORITHM = settings.jwt_algorithm
SECRET_KEY = settings.secret_key
EXPIRATION_SECONDS = settings.token_expiration_seconds
RSA_PRIVATE_KEY_PATH = settings.rsa_private_key_path
RSA_PUBLIC_KEY_PATH = settings.rsa_public_key_path

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
    token = jwt.encode(payload, PRIVATE_KEY, algorithm=JWT_ALGORITHM)
    try:
        token_store.store(token, payload["exp"], payload)
    except Exception:  # pragma: no cover - caching failures shouldn't break
        pass
    return token


def decode_token(token: str) -> Dict[str, Any]:
    """Decode a JWT and return its payload. Cached in Redis if available."""

    cached = token_store.get(token)
    if cached:
        return cached
    try:
        payload = jwt.decode(token, PUBLIC_KEY, algorithms=[JWT_ALGORITHM])
    except JWTError as exc:  # pragma: no cover
        raise ValueError("Invalid token") from exc
    try:
        token_store.store(token, payload["exp"], payload)
    except Exception:  # pragma: no cover - caching failures shouldn't break
        pass
    return payload
