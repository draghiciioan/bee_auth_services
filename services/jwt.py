import base64
import json
import os
import time
from typing import Dict

import hmac
import hashlib

SECRET_KEY = os.getenv("SECRET_KEY", "secret")
ALGORITHM = "HS256"
EXPIRATION_SECONDS = 7200


def _sign(message: bytes) -> str:
    return base64.urlsafe_b64encode(
        hmac.new(SECRET_KEY.encode(), message, hashlib.sha256).digest()
    ).decode().rstrip("=")


def create_token(data: Dict[str, str], expires_delta: int | None = None) -> str:
    header = {"alg": ALGORITHM, "typ": "JWT"}
    payload = data.copy()
    expire = int(time.time()) + (expires_delta or EXPIRATION_SECONDS)
    payload["exp"] = expire
    segments = [
        base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip("="),
        base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("="),
    ]
    signature = _sign(".".join(segments).encode())
    return ".".join(segments + [signature])


def decode_token(token: str) -> Dict[str, str]:
    try:
        header_b64, payload_b64, signature = token.split(".")
        message = f"{header_b64}.{payload_b64}".encode()
        expected_sig = _sign(message)
        if not hmac.compare_digest(expected_sig, signature):
            raise ValueError("Invalid signature")
        payload = json.loads(base64.urlsafe_b64decode(payload_b64 + "=="))
        if payload.get("exp", 0) < int(time.time()):
            raise ValueError("Token expired")
        return payload
    except Exception as exc:  # pylint: disable=broad-except
        raise ValueError("Invalid token") from exc
