import asyncio
from unittest.mock import ANY, patch

import pytest
import time
from fastapi import HTTPException
from utils.errors import ErrorCode

from fastapi import BackgroundTasks
from models import LoginAttempt, User
from routers.auth import login
from schemas.user import UserLogin
from services import jwt as jwt_service
from utils import hash_password
from utils.settings import settings


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
    bg = BackgroundTasks()
    with patch("events.rabbitmq.emit_event") as emit_mock, patch(
        "routers.auth.emit_event", emit_mock
    ):
        result = login(req, creds, bg, db=session)
        asyncio.run(bg())
    assert "access_token" in result

    payload = jwt_service.decode_token(result["access_token"])
    assert payload["sub"] == str(user.id)
    assert payload["role"] == user.role.value
    assert payload["email"] == user.email
    assert payload["provider"] == "local"

    attempt = session.query(LoginAttempt).filter_by(user_id=user.id).first()
    assert attempt is not None
    assert attempt.success is True
    assert attempt.email_attempted == user.email
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


def test_login_invalid_password_records_attempt(session):
    user = create_verified_user(session)
    req = DummyRequest()
    creds = UserLogin(email=user.email, password="Wrong123!")
    bg = BackgroundTasks()
    with patch("events.rabbitmq.emit_event") as emit_mock, patch(
        "routers.auth.emit_event", emit_mock
    ):
        with pytest.raises(HTTPException) as exc:
            login(req, creds, bg, db=session)
        asyncio.run(bg())
    assert exc.value.status_code == 400
    assert exc.value.detail == {
        "code": ErrorCode.INVALID_CREDENTIALS,
        "message": "Invalid credentials",
    }
    attempt = session.query(LoginAttempt).filter_by(user_id=user.id).first()
    assert attempt.success is False
    assert attempt.email_attempted == user.email
    emit_mock.assert_not_called()


def test_login_unknown_email_records_attempt(session):
    req = DummyRequest()
    creds = UserLogin(email="unknown@example.com", password="Secret123!")
    bg = BackgroundTasks()
    with patch("events.rabbitmq.emit_event") as emit_mock, patch(
        "routers.auth.emit_event", emit_mock
    ):
        with pytest.raises(HTTPException) as exc:
            login(req, creds, bg, db=session)
        asyncio.run(bg())
    assert exc.value.status_code == 400
    assert exc.value.detail == {
        "code": ErrorCode.INVALID_CREDENTIALS,
        "message": "Invalid credentials",
    }
    attempt = (
        session.query(LoginAttempt)
        .filter_by(email_attempted="unknown@example.com")
        .first()
    )
    assert attempt.user_id is None
    assert attempt.success is False
    emit_mock.assert_not_called()


def test_login_lockout_after_failed_attempts(session, monkeypatch):
    monkeypatch.setattr(settings, "login_attempt_threshold", 2)
    monkeypatch.setattr(settings, "login_attempt_window_seconds", 60)

    user = create_verified_user(session)
    req = DummyRequest()
    wrong_creds = UserLogin(email=user.email, password="Bad123!")
    bg = BackgroundTasks()
    with patch("events.rabbitmq.emit_event") as emit_mock, patch(
        "routers.auth.emit_event", emit_mock
    ):
        for _ in range(2):
            with pytest.raises(HTTPException):
                login(req, wrong_creds, bg, db=session)
        with pytest.raises(HTTPException) as exc:
            login(req, UserLogin(email=user.email, password="Secret123!"), bg, db=session)
        asyncio.run(bg())
    assert exc.value.status_code == 429
    assert exc.value.detail == {
        "code": ErrorCode.TOO_MANY_FAILED_ATTEMPTS,
        "message": "Too many failed login attempts. Please try again later.",
    }
    emit_mock.assert_not_called()


def test_login_unlocks_after_timeout(session, monkeypatch):
    monkeypatch.setattr(settings, "login_attempt_threshold", 1)
    monkeypatch.setattr(settings, "login_attempt_window_seconds", 1)

    user = create_verified_user(session)
    req = DummyRequest()
    wrong_creds = UserLogin(email=user.email, password="Bad123!")
    bg = BackgroundTasks()
    with patch("events.rabbitmq.emit_event") as emit_mock, patch(
        "routers.auth.emit_event", emit_mock
    ):
        with pytest.raises(HTTPException):
            login(req, wrong_creds, bg, db=session)
        time.sleep(1.1)
        result = login(req, UserLogin(email=user.email, password="Secret123!"), bg, db=session)
        asyncio.run(bg())
    assert "access_token" in result
    emit_mock.assert_called()
