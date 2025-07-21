from datetime import datetime, timedelta

from routers.auth import login, verify_twofa
from services import auth as auth_service
from models import User, TwoFAToken
from schemas.user import UserLogin, TwoFAVerify


class DummyRequest:
    def __init__(self):
        self.client = type("client", (), {"host": "127.0.0.1"})()
        self.headers = {"user-agent": "pytest"}


def create_verified_user(session):
    user = User(
        email="user@example.com",
        hashed_password=auth_service.hash_password("Secret123!"),
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
    response = login(req, credentials, db=session)
    assert response["message"] == "2fa_required"
    token_value = response["twofa_token"]
    record = session.query(TwoFAToken).filter_by(token=token_value).first()
    assert record is not None
    assert record.user_id == user.id
    assert not record.is_used
    delta = record.expires_at - datetime.utcnow()
    assert timedelta(0) < delta <= timedelta(minutes=5)


def test_verify_twofa_marks_token_used_and_returns_jwt(session):
    user = create_verified_user(session)
    token = auth_service.create_twofa_token(session, user)
    payload = TwoFAVerify(twofa_token=token.token)
    response = verify_twofa(payload, db=session)
    assert "access_token" in response
    session.refresh(token)
    assert token.is_used is True
