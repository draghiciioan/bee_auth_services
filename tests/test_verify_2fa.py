import asyncio
from unittest.mock import ANY, patch

import pytest
from pydantic import ValidationError

from fastapi import BackgroundTasks
from models import TwoFAToken, User
import pyotp
from routers.auth import login, verify_twofa
from schemas.user import TwoFAVerify, UserLogin
from services import auth as auth_service, jwt as jwt_service
from utils import hash_password


class DummyRequest:
    def __init__(self) -> None:
        self.client = type("client", (), {"host": "127.0.0.1"})()
        self.headers = {"user-agent": "pytest"}


def create_twofa_user(session) -> User:
    user = User(
        email="2fa@example.com",
        hashed_password=hash_password("Secret123!"),
        totp_secret=pyotp.random_base32(),
        is_email_verified=True,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def test_login_returns_twofa_token(session):
    user = create_twofa_user(session)
    req = DummyRequest()
    creds = UserLogin(email=user.email, password="Secret123!")
    bg = BackgroundTasks()
    with patch("events.rabbitmq.emit_event") as emit_mock, patch(
        "routers.auth.emit_event", emit_mock
    ):
        result = login(req, creds, bg, db=session)
        asyncio.run(bg())
    assert result["message"] == "2fa_required"
    token = session.query(TwoFAToken).filter_by(user_id=user.id).first()
    assert token is not None
    assert len(token.token) == 12
    assert result["twofa_token"] == token.token
    emit_mock.assert_called_once_with(
        "user.2fa_requested",
        {
            "event_id": ANY,
            "timestamp": ANY,
            "user_id": user.id,
            "email": user.email,
            "provider": "local",
        },
    )


def test_verify_twofa_returns_jwt_and_marks_used(session):
    user = create_twofa_user(session)
    token = auth_service.create_twofa_token(session, user)
    assert len(token.token) == 12
    code = pyotp.TOTP(user.totp_secret).now()
    payload = TwoFAVerify(twofa_token=token.token, totp_code=code)
    bg = BackgroundTasks()
    with patch("events.rabbitmq.emit_event") as emit_mock, patch(
        "routers.auth.emit_event", emit_mock
    ):
        response = verify_twofa(payload, bg, db=session)
        asyncio.run(bg())
    assert "access_token" in response
    jwt_payload = jwt_service.decode_token(response["access_token"])
    assert jwt_payload["sub"] == str(user.id)
    assert jwt_payload["email"] == user.email
    assert jwt_payload["provider"] == "local"
    session.refresh(token)
    assert token.is_used is True
    emit_mock.assert_called_once_with(
        "user.logged_in",
        {
            "event_id": ANY,
            "timestamp": ANY,
            "user_id": user.id,
            "email": user.email,
            "provider": "local",
        },
    )


def test_verify_twofa_invalid_token(session):
    with pytest.raises(ValidationError):
        verify_twofa(
            TwoFAVerify(twofa_token="wrong", totp_code="000000"),
            BackgroundTasks(),
            db=session,
        )
