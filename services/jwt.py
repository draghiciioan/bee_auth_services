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
import secrets
from typing import Any, Dict

from jose import JWTError, jwt

from utils import token_store
from utils.settings import settings

JWT_ALGORITHM = settings.jwt_algorithm
SECRET_KEY = settings.secret_key
EXPIRATION_SECONDS = settings.token_expiration_seconds
REFRESH_EXPIRATION_SECONDS = settings.refresh_token_expiration_seconds
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


def create_refresh_token(
    *,
    user_id: str,
    email: str,
    role: str,
    provider: str,
    expires_delta: timedelta | None = None,
) -> str:
    """Generate a random refresh token stored in Redis."""

    now = datetime.now(timezone.utc)
    expire = now + (
        expires_delta or timedelta(seconds=REFRESH_EXPIRATION_SECONDS)
    )
    payload = {
        "sub": user_id,
        "email": email,
        "role": role,
        "provider": provider,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }
    token = secrets.token_urlsafe(32)
    try:
        token_store.store_refresh(token, payload["exp"], payload)
    except Exception:  # pragma: no cover
        pass
    return token


def decode_refresh_token(token: str) -> Dict[str, Any]:
    """Validate a refresh token stored in Redis."""

    payload = token_store.get_refresh(token)
    if not payload:
        raise ValueError("Invalid token")
    if token_store.is_revoked(token):
        raise ValueError("Token revoked")
    if payload["exp"] < int(datetime.now(timezone.utc).timestamp()):
        raise ValueError("Invalid token")
    return payload


def decode_token(token: str) -> Dict[str, Any]:
    """Decode a JWT and return its payload. Cached in Redis if available."""

    cached = token_store.get(token)
    if cached:
        if token_store.is_revoked(token):
            raise ValueError("Token revoked")
        return cached
    try:
        payload = jwt.decode(token, PUBLIC_KEY, algorithms=[JWT_ALGORITHM])
    except JWTError as exc:  # pragma: no cover
        raise ValueError("Invalid token") from exc
    if token_store.is_revoked(token):
        raise ValueError("Token revoked")
    try:
        token_store.store(token, payload["exp"], payload)
    except Exception:  # pragma: no cover - caching failures shouldn't break
        pass
    return payload


def revoke_refresh_token(token: str) -> None:
    """Mark a refresh token as revoked in the store."""

    payload = token_store.get_refresh(token)
    exp = payload["exp"] if payload else int(
        datetime.now(timezone.utc).timestamp() + REFRESH_EXPIRATION_SECONDS
    )
    try:
        token_store.revoke_refresh(token, exp)
    except Exception:  # pragma: no cover
        pass
