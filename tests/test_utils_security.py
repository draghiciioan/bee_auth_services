import pytest

def _import_modules(monkeypatch):
    import importlib
    from utils import security
    from services import jwt as jwt_service

    importlib.reload(security)
    importlib.reload(jwt_service)

    from utils import hash_password, verify_password

    return hash_password, verify_password, jwt_service


def test_password_hashing_and_verification(monkeypatch):
    password = "Secret123!"
    hash_password, verify_password, _ = _import_modules(monkeypatch)
    hashed = hash_password(password)
    assert hashed != password
    assert verify_password(password, hashed)


def test_jwt_creation_and_decoding(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "testsecret")
    # Use a longer expiration time for the initial token validation
    monkeypatch.setenv("TOKEN_EXPIRATION_SECONDS", "3600")  # 1 hour
    _, _, jwt_mod = _import_modules(monkeypatch)
    from utils import token_store
    token_store._redis_client = None
    token = jwt_mod.create_token(
        user_id="123",
        email="t@example.com",
        role="client",
        provider="local",
    )
    payload = jwt_mod.decode_token(token)
    assert payload["sub"] == "123"

    # For testing expiration, create a token with a very short expiration
    monkeypatch.setenv("TOKEN_EXPIRATION_SECONDS", "1")
    # Reload the module to pick up the new environment variable
    _, _, jwt_mod = _import_modules(monkeypatch)
    short_token = jwt_mod.create_token(
        user_id="123",
        email="t@example.com",
        role="client",
        provider="local",
    )
    
    # token should expire after 1 second
    import time
    time.sleep(2)
    with pytest.raises(Exception):
        jwt_mod.decode_token(short_token)
