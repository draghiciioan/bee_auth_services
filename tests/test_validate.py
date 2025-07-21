import hashlib
import importlib
import json
from datetime import timedelta
from pathlib import Path

import fakeredis
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

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


def test_validate_expired_token():
    setup_fake_cache()
    token = jwt_service.create_token(
        user_id="1",
        email="t@example.com",
        role="client",
        provider="local",
        expires_delta=timedelta(seconds=-1),
    )
    response = validate(token)
    assert response.status_code == 401
    body = json.loads(response.body.decode())
    assert body["valid"] is False


def _gen_rsa_keys(tmp_path: Path) -> tuple[Path, Path]:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    priv_path = tmp_path / "priv.pem"
    pub_path = tmp_path / "pub.pem"
    priv_path.write_bytes(
        private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    pub_path.write_bytes(
        private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )
    return priv_path, pub_path


def test_validate_rs256_and_edge_cases(monkeypatch, tmp_path):
    fake = setup_fake_cache()
    priv, pub = _gen_rsa_keys(tmp_path)

    monkeypatch.setenv("JWT_ALGORITHM", "RS256")
    monkeypatch.setenv("RSA_PRIVATE_KEY_PATH", str(priv))
    monkeypatch.setenv("RSA_PUBLIC_KEY_PATH", str(pub))

    import services.jwt as jwt_mod
    jwt_mod = importlib.reload(jwt_mod)

    token = jwt_mod.create_token(
        user_id="2", email="r@t.com", role="client", provider="local"
    )
    resp = validate(token)
    assert resp["valid"] is True
    key = hashlib.sha256(token.encode()).hexdigest()
    assert json.loads(fake.get(key))["sub"] == "2"

    tampered = token[:-1] + ("a" if token[-1] != "a" else "b")
    bad_resp = validate(tampered)
    assert bad_resp.status_code == 401

    malformed_resp = validate("abc.def")
    assert malformed_resp.status_code == 401
