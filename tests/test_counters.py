import asyncio
from unittest.mock import patch

import asyncio
from unittest.mock import patch

import fakeredis
import pytest
from fastapi import BackgroundTasks, HTTPException

from models import User
from routers.auth import login, register
from schemas.user import UserCreate, UserLogin
from utils import (
    hash_password,
    login_success_counter,
    register_failed_counter,
    token_store,
)


class DummyRequest:
    def __init__(self) -> None:
        self.client = type("client", (), {"host": "127.0.0.1"})()
        self.headers = {"user-agent": "pytest"}


def setup_cache() -> None:
    token_store._redis_client = fakeredis.FakeRedis(decode_responses=True)


def test_login_success_counter_increment(session):
    setup_cache()
    login_success_counter._value.set(0)
    user = User(
        email="metric@example.com",
        hashed_password=hash_password("Secret123!"),
        is_email_verified=True,
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    req = DummyRequest()
    creds = UserLogin(email=user.email, password="Secret123!")
    bg = BackgroundTasks()
    with patch("events.rabbitmq.emit_event") as emit_mock, patch(
        "routers.auth.emit_event",
        emit_mock,
    ):
        login(req, creds, bg, db=session)
        asyncio.run(bg())

    assert login_success_counter._value.get() == 1


def test_register_failed_counter_increment(session):
    setup_cache()
    register_failed_counter._value.set(0)
    user = User(email="dupe@example.com", hashed_password="hash")
    session.add(user)
    session.commit()

    payload = UserCreate(email="dupe@example.com", password="Strong1!")
    bg = BackgroundTasks()
    with patch("events.rabbitmq.emit_event") as emit_mock, patch(
        "routers.auth.emit_event",
        emit_mock,
    ):
        with pytest.raises(HTTPException):
            register(payload, bg, db=session)
        asyncio.run(bg())

    assert register_failed_counter._value.get() == 1
    emit_mock.assert_not_called()

