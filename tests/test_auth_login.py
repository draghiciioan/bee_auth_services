from unittest.mock import patch

import pytest
from fastapi import HTTPException

from models import LoginAttempt, User
from routers.auth import login
from schemas.user import UserLogin
from services import jwt as jwt_service
from utils import hash_password


class DummyRequest:
    def __init__(self) -> None:
        self.client = type("client", (), {"host": "127.0.0.1"})()
        self.headers = {"user-agent": "pytest"}


def create_verified_user(session) -> User:
    user = User(
        email="login@example.com",
        hashed_password=hash_password("Secret123!"),
        is_email_verified=True,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def test_login_success_records_attempt_and_returns_jwt(session):
    user = create_verified_user(session)
    req = DummyRequest()
    creds = UserLogin(email=user.email, password="Secret123!")
    with patch("routers.auth.emit_event"):
        result = login(req, creds, db=session)
    assert "access_token" in result

    payload = jwt_service.decode_token(result["access_token"])
    assert payload["sub"] == str(user.id)
    assert payload["role"] == user.role.value
    assert payload["email"] == user.email
    assert payload["provider"] == "local"

    attempt = session.query(LoginAttempt).filter_by(user_id=user.id).first()
    assert attempt is not None
    assert attempt.success is True


def test_login_invalid_password_records_attempt(session):
    user = create_verified_user(session)
    req = DummyRequest()
    creds = UserLogin(email=user.email, password="Wrong123!")
    with patch("routers.auth.emit_event"):
        with pytest.raises(HTTPException) as exc:
            login(req, creds, db=session)
    assert exc.value.status_code == 400
    attempt = session.query(LoginAttempt).filter_by(user_id=user.id).first()
    assert attempt.success is False
