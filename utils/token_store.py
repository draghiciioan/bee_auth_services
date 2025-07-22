import hashlib
import json
import os
from datetime import datetime, timezone
from typing import Any, Optional

import redis

_redis_client: Optional[redis.Redis] = None


def _get_client() -> Optional[redis.Redis]:
    global _redis_client
    if _redis_client is not None:
        return _redis_client

    host = os.getenv("REDIS_HOST", "redis")
    port = int(os.getenv("REDIS_PORT", 6379))
    db = int(os.getenv("REDIS_DB", 0))
    password = os.getenv("REDIS_PASSWORD")
    try:
        _redis_client = redis.Redis(
            host=host, port=port, db=db, password=password, decode_responses=True
        )
        _redis_client.ping()
    except Exception:
        _redis_client = None
    return _redis_client


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


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
