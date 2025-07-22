import fakeredis
import pytest
from fastapi import HTTPException

from routers.auth import refresh, logout
from services import jwt as jwt_service
from utils import token_store
from models import User
from schemas.user import RefreshTokenRequest, LogoutRequest
from utils import hash_password


class DummyRequest:
    def __init__(self):
        self.client = type("client", (), {"host": "127.0.0.1"})()
        self.headers = {"user-agent": "pytest"}


def setup_cache():
    token_store._redis_client = fakeredis.FakeRedis(decode_responses=True)


def create_user(session):
    user = User(
        email="refresh@example.com",
        hashed_password=hash_password("Secret123!"),
        is_email_verified=True,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def test_refresh_returns_new_access_token(session):
    setup_cache()
    user = create_user(session)
    refresh_token = jwt_service.create_refresh_token(
        user_id=str(user.id),
        email=user.email,
        role=user.role.value,
        provider="local",
    )
    request = RefreshTokenRequest(refresh_token=refresh_token)
    response = refresh(request)
    assert "access_token" in response
    payload = jwt_service.decode_token(response["access_token"])
    assert payload["sub"] == str(user.id)


def test_logout_revokes_refresh_token(session):
    setup_cache()
    user = create_user(session)
    refresh_token = jwt_service.create_refresh_token(
        user_id=str(user.id),
        email=user.email,
        role=user.role.value,
        provider="local",
    )
    logout(LogoutRequest(refresh_token=refresh_token))
    with pytest.raises(HTTPException):
        refresh(RefreshTokenRequest(refresh_token=refresh_token))

