import asyncio
from starlette.requests import Request

from utils.rate_limit import user_rate_limit_key
from services import jwt as jwt_service


async def _receive_json(body: bytes):
    return {"type": "http.request", "body": body, "more_body": False}


def _make_request(headers=None, body=b"{}", method="GET"):
    headers = headers or {}
    scope = {
        "type": "http",
        "path": "/dummy",
        "method": method,
        "headers": [(k.lower().encode(), v.encode()) for k, v in headers.items()],
        "client": ("127.0.0.1", 12345),
    }
    async def receive():
        return await _receive_json(body)

    return Request(scope, receive=receive)


def test_identifier_from_jwt():
    token = jwt_service.create_token(
        user_id="abc", email="t@example.com", role="client", provider="local"
    )
    req = _make_request(headers={"Authorization": f"Bearer {token}"})
    key = asyncio.run(user_rate_limit_key(req))
    assert key.startswith("abc:")


def test_identifier_from_body():
    body = b'{"email": "body@example.com"}'
    req = _make_request(method="POST", body=body)
    key = asyncio.run(user_rate_limit_key(req))
    assert key.startswith("body@example.com:")
