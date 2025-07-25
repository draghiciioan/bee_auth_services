from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from utils.errors import ErrorCode

from models import User, EmailVerification
from services import auth as auth_service
from routers.auth import verify_email


def test_verify_email_success(session):
    user = User(email="a@example.com", hashed_password="hash")
    session.add(user)
    session.commit()

    record = auth_service.create_email_verification(session, user)
    response = verify_email(token=record.token, db=session)

    assert response == {"message": "email_verified"}
    session.refresh(user)
    assert user.is_email_verified is True
    assert session.query(EmailVerification).count() == 0


def test_verify_email_invalid(session):
    try:
        verify_email(token="invalid", db=session)
        assert False, "Should have raised"
    except HTTPException as exc:
        assert exc.status_code == 400
        assert exc.detail == {
            "code": ErrorCode.INVALID_TOKEN,
            "message": "Invalid token",
        }


def test_verify_email_expired_token(session):
    user = User(email="expired@example.com", hashed_password="hash")
    session.add(user)
    session.commit()

    expired = EmailVerification(
        user_id=user.id,
        token="expired",
        expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
    )
    session.add(expired)
    session.commit()

    try:
        verify_email(token="expired", db=session)
        assert False, "Should have raised"
    except HTTPException as exc:
        assert exc.status_code == 400
        assert exc.detail == {
            "code": ErrorCode.INVALID_TOKEN,
            "message": "Invalid token",
        }
