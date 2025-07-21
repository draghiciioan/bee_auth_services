from datetime import timedelta
import os


def _import_security():
    import importlib
    from utils import security

    importlib.reload(security)

    from utils import (
        hash_password,
        verify_password,
        create_access_token,
        decode_access_token,
    )

    return hash_password, verify_password, create_access_token, decode_access_token


def test_password_hashing_and_verification():
    password = "Secret123!"
    hash_password, verify_password, _, _ = _import_security()
    hashed = hash_password(password)
    assert hashed != password
    assert verify_password(password, hashed)


def test_jwt_creation_and_decoding(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "testsecret")
    monkeypatch.setenv("TOKEN_EXPIRATION_SECONDS", "1")
    _, _, create_access_token, decode_access_token = _import_security()
    token = create_access_token({"sub": "123"})
    payload = decode_access_token(token)
    assert payload["sub"] == "123"

    # token should expire after 1 second
    import time
    time.sleep(2)
    try:
        decode_access_token(token)
        assert False, "Expired token not detected"
    except ValueError:
        assert True
