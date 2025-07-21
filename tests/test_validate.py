import hashlib
import json

import fakeredis

from routers.auth import validate
from services import jwt as jwt_service
from utils import token_store


def setup_fake_cache():
    fake = fakeredis.FakeRedis(decode_responses=True)
    token_store._redis_client = fake
    return fake


def test_validate_success_cached(monkeypatch):
    fake = setup_fake_cache()
    token = jwt_service.create_token(
        user_id="1", email="t@example.com", role="client", provider="local"
    )
    resp = validate(token)
    assert resp["valid"] is True
    key = hashlib.sha256(token.encode()).hexdigest()
    cached = json.loads(fake.get(key))
    assert cached["sub"] == "1"

    class DummyJWT:
        def decode(self, *args, **kwargs):
            raise AssertionError("should not decode")

    monkeypatch.setattr(jwt_service, "jwt", DummyJWT())
    resp2 = validate(token)
    assert resp2["valid"] is True


def test_validate_invalid_token():
    setup_fake_cache()
    response = validate("bad")
    assert isinstance(response, object)
    assert response.status_code == 401
    body = json.loads(response.body.decode())
    assert body["valid"] is False
