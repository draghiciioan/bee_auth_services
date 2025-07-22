from __future__ import annotations

from fastapi import Request

# This helper is used by FastAPI-Limiter to generate a rate limit key
# that combines the authenticated user's identifier with the client IP.

from services import jwt as jwt_service


async def user_rate_limit_key(request: Request) -> str:
    """Build a rate limit key using the user identifier and client IP."""
    user_part = None
    auth = request.headers.get("Authorization")
    if auth and auth.startswith("Bearer "):
        token = auth.split(" ", 1)[1]
        try:
            payload = jwt_service.decode_token(token)
            user_part = payload.get("sub") or payload.get("email")
        except Exception:  # pragma: no cover - invalid token
            user_part = None
    if user_part is None and request.method in {"POST", "PUT", "PATCH"}:
        try:
            data = await request.json()
            user_part = data.get("email")
        except Exception:  # pragma: no cover - body issues
            user_part = None
    forwarded = request.headers.get("X-Forwarded-For")
    ip = forwarded.split(",")[0] if forwarded else request.client.host
    return f"{user_part or 'anon'}:{ip}"
