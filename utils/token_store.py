import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Optional

import redis

from .settings import settings

_redis_client: Optional[redis.Redis] = None


def _get_client() -> Optional[redis.Redis]:
    global _redis_client
    if _redis_client is not None:
        return _redis_client

    try:
        _redis_client = redis.Redis.from_url(
            settings.redis_url, decode_responses=True
        )
        _redis_client.ping()
    except Exception:
        _redis_client = None
    return _redis_client


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


REVOKED_PREFIX = "revoked:"
REFRESH_PREFIX = "refresh:"


def store(token: str, exp: int, payload: dict[str, Any]) -> None:
    client = _get_client()
    if not client:
        return
    ttl = exp - int(datetime.now(timezone.utc).timestamp())
    if ttl <= 0:
        return
    client.setex(_hash(token), ttl, json.dumps(payload))


def get(token: str) -> Optional[dict[str, Any]]:
    client = _get_client()
    if not client:
        return None
    data = client.get(_hash(token))
    if data:
        try:
            return json.loads(data)
        except json.JSONDecodeError:
            return None
    return None


def store_refresh(token: str, exp: int, payload: dict[str, Any]) -> None:
    client = _get_client()
    if not client:
        return
    ttl = exp - int(datetime.now(timezone.utc).timestamp())
    if ttl <= 0:
        return
    client.setex(f"{REFRESH_PREFIX}{_hash(token)}", ttl, json.dumps(payload))


def get_refresh(token: str) -> Optional[dict[str, Any]]:
    client = _get_client()
    if not client:
        return None
    data = client.get(f"{REFRESH_PREFIX}{_hash(token)}")
    if data:
        try:
            return json.loads(data)
        except json.JSONDecodeError:
            return None
    return None


def revoke(token: str, exp: int) -> None:
    client = _get_client()
    if not client:
        return
    ttl = exp - int(datetime.now(timezone.utc).timestamp())
    if ttl <= 0:
        ttl = 0
    client.setex(f"{REVOKED_PREFIX}{_hash(token)}", ttl or 1, "1")


def is_revoked(token: str) -> bool:
    client = _get_client()
    if not client:
        return False
    return bool(client.exists(f"{REVOKED_PREFIX}{_hash(token)}"))


def revoke_refresh(token: str, exp: int) -> None:
    client = _get_client()
    if not client:
        return
    ttl = exp - int(datetime.now(timezone.utc).timestamp())
    if ttl <= 0:
        ttl = 0
    client.delete(f"{REFRESH_PREFIX}{_hash(token)}")
    client.setex(f"{REVOKED_PREFIX}{_hash(token)}", ttl or 1, "1")
