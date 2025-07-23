import pyotp

from routers.auth import setup_twofa
from models import User
from services import jwt as jwt_service
from utils import hash_password


def create_user(session) -> User:
    user = User(
        email="setup@example.com",
        hashed_password=hash_password("Secret123!"),
        is_email_verified=True,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def test_setup_twofa_persists_secret_and_returns_uri(session):
    user = create_user(session)
    token = jwt_service.create_token(
        user_id=str(user.id),
        email=user.email,
        role=user.role.value,
        provider="local",
    )
    result = setup_twofa(token=token, db=session)
    session.refresh(user)
    assert user.totp_secret is not None
    expected_uri = pyotp.totp.TOTP(user.totp_secret).provisioning_uri(
        name=user.email,
        issuer_name="BeeConect",
    )
    assert result["provisioning_uri"] == expected_uri
