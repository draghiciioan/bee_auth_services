import asyncio
from unittest.mock import ANY, patch

import pytest
from fastapi import BackgroundTasks
from pydantic import ValidationError

from routers.auth import request_password_reset, reset_password
from schemas.user import PasswordResetRequest, PasswordReset
from models import User, PasswordResetToken
from services import auth as auth_service
from utils import hash_password, verify_password


def create_user(session) -> User:
    user = User(
        email="reset@example.com",
        hashed_password=hash_password("OldPass1!"),
        is_email_verified=True,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def test_request_password_reset_creates_token_and_emits_event(session):
    user = create_user(session)
    bg = BackgroundTasks()
    with patch("events.rabbitmq.emit_event") as emit_mock, patch(
        "routers.auth.emit_event", emit_mock
    ):
        response = request_password_reset(
            PasswordResetRequest(email=user.email), bg, db=session
        )
        asyncio.run(bg())
    assert response == {"message": "reset_requested"}
    token = session.query(PasswordResetToken).filter_by(user_id=user.id).first()
    assert token is not None
    emit_mock.assert_called_once_with(
        "user.password_reset_requested",
        {
            "event_id": ANY,
            "timestamp": ANY,
            "user_id": user.id,
            "email": user.email,
            "token": token.token,
        },
    )


def test_reset_password_updates_hash_and_marks_token_used(session):
    user = create_user(session)
    token = auth_service.create_password_reset_token(session, user)
    payload = PasswordReset(token=token.token, new_password="NewPass1!")
    response = reset_password(payload, db=session)
    assert response == {"message": "password_reset"}
    session.refresh(user)
    session.refresh(token)
    assert verify_password("NewPass1!", user.hashed_password)
    assert token.used is True


def test_reset_password_invalid_token(session):
    with pytest.raises(ValidationError):
        reset_password(
            PasswordReset(token="bad", new_password="NewPass1!"), db=session
        )
