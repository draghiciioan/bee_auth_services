import asyncio
from unittest.mock import ANY, call, patch

import pytest
from fastapi import HTTPException

from models import EmailVerification, User
from fastapi import BackgroundTasks
from routers.auth import register
from schemas.user import UserCreate


def test_register_success_creates_user_and_verification(session):
    payload = UserCreate(
        email="new@example.com",
        password="Strong1!",
        full_name="New User",
        phone_number="+40721111222",
    )
    bg = BackgroundTasks()
    with patch("events.rabbitmq.emit_event") as emit_mock, patch(
        "routers.auth.emit_event", emit_mock
    ):
        response = register(payload, bg, db=session)
        asyncio.run(bg())

    emit_mock.assert_has_calls(
        [
            call(
                "user.registered",
                {
                    "event_id": ANY,
                    "timestamp": ANY,
                    "user_id": response.id,
                    "email": payload.email,
                    "provider": None,
                },
            ),
            call(
                "user.email_verification_sent",
                {
                    "event_id": ANY,
                    "timestamp": ANY,
                    "user_id": response.id,
                    "email": payload.email,
                    "provider": None,
                },
            ),
        ]
    )

    user = session.query(User).filter_by(email="new@example.com").first()
    assert user is not None
    assert user.hashed_password != "Strong1!"
    assert session.query(EmailVerification).filter_by(user_id=user.id).count() == 1
    assert response.email == payload.email
    assert response.full_name == payload.full_name


def test_register_duplicate_email_fails(session):
    user = User(email="dupe@example.com", hashed_password="hash")
    session.add(user)
    session.commit()

    payload = UserCreate(
        email="dupe@example.com",
        password="Strong1!",
    )
    bg = BackgroundTasks()
    with patch("events.rabbitmq.emit_event") as emit_mock, patch(
        "routers.auth.emit_event", emit_mock
    ):
        with pytest.raises(HTTPException) as exc:
            register(payload, bg, db=session)
        asyncio.run(bg())
    assert exc.value.status_code == 400
    emit_mock.assert_not_called()
