from datetime import datetime, timedelta

import asyncio
from unittest.mock import ANY, patch

from fastapi import BackgroundTasks
from routers.auth import login, verify_twofa
from services import auth as auth_service
from utils import hash_password
from models import User, TwoFAToken
from schemas.user import UserLogin, TwoFAVerify


class DummyRequest:
    def __init__(self):
        self.client = type("client", (), {"host": "127.0.0.1"})()
        self.headers = {"user-agent": "pytest"}


def create_verified_user(session):
    user = User(
        email="user@example.com",
        hashed_password=hash_password("Secret123!"),
        phone_number="+40721234567",
        is_email_verified=True,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def test_login_returns_twofa_token(session):
    user = create_verified_user(session)
    req = DummyRequest()
    credentials = UserLogin(email=user.email, password="Secret123!")
    bg = BackgroundTasks()
    with patch("events.rabbitmq.emit_event") as emit_mock, patch(
        "routers.auth.emit_event", emit_mock
    ):
        response = login(req, credentials, bg, db=session)
        asyncio.run(bg())
    assert response["message"] == "2fa_required"
    token_value = response["twofa_token"]
    record = session.query(TwoFAToken).filter_by(token=token_value).first()
    assert record is not None
    assert record.user_id == user.id
    assert not record.is_used
    delta = record.expires_at - datetime.utcnow()
    assert timedelta(0) < delta <= timedelta(minutes=5)
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


def test_verify_twofa_marks_token_used_and_returns_jwt(session):
    user = create_verified_user(session)
    token = auth_service.create_twofa_token(session, user)
    payload = TwoFAVerify(twofa_token=token.token)
    bg = BackgroundTasks()
    with patch("events.rabbitmq.emit_event") as emit_mock, patch(
        "routers.auth.emit_event", emit_mock
    ):
        response = verify_twofa(payload, bg, db=session)
        asyncio.run(bg())
    assert "access_token" in response
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
