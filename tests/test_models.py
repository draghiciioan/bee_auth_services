from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.exc import IntegrityError

from models import User, LoginAttempt, EmailVerification, TwoFAToken


def test_user_email_uniqueness(session):
    user1 = User(email="a@example.com", hashed_password="hash")
    session.add(user1)
    session.commit()

    user2 = User(email="a@example.com", hashed_password="hash")
    session.add(user2)
    with pytest.raises(IntegrityError):
        session.commit()


def test_user_email_required(session):
    user = User(hashed_password="hash")
    session.add(user)
    with pytest.raises(IntegrityError):
        session.commit()


def test_user_default_values(session):
    user = User(email="b@example.com", hashed_password="hash")
    session.add(user)
    session.commit()
    assert user.is_active is True
    assert user.is_email_verified is False
    assert user.is_social is False


def test_login_attempt_creation(session):
    user = User(email="c@example.com", hashed_password="hash")
    session.add(user)
    session.commit()

    attempt = LoginAttempt(
        user_id=user.id,
        ip_address="127.0.0.1",
        user_agent="pytest",
        email_attempted=user.email,
    )
    session.add(attempt)
    session.commit()

    retrieved = session.query(LoginAttempt).first()
    assert retrieved.ip_address == "127.0.0.1"
    assert retrieved.user_agent == "pytest"
    assert retrieved.user_id == user.id
    assert retrieved.success is False
    assert retrieved.email_attempted == user.email


def test_email_verification_link(session):
    user = User(email="d@example.com", hashed_password="hash")
    session.add(user)
    session.commit()

    ev = EmailVerification(
        user_id=user.id,
        token="token123",
        expires_at=datetime.now(timezone.utc) + timedelta(days=1),
    )
    session.add(ev)
    session.commit()

    retrieved = session.query(EmailVerification).first()
    assert retrieved.user_id == user.id
    assert retrieved.token == "token123"


def test_twofa_token_link(session):
    user = User(email="e@example.com", hashed_password="hash")
    session.add(user)
    session.commit()

    token = TwoFAToken(
        user_id=user.id,
        token="654321",
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
    )
    session.add(token)
    session.commit()

    retrieved = session.query(TwoFAToken).first()
    assert retrieved.user_id == user.id
    assert retrieved.token == "654321"
    assert retrieved.is_used is False
