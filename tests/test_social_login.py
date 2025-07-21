from unittest.mock import patch

from fastapi import BackgroundTasks
from models import User
from routers.auth import social_callback, social_login
from schemas.user import SocialLogin
from services import jwt as jwt_service


def test_social_login_url_generation():
    response = social_login("google")
    assert response["login_url"].startswith("https://google.com/oauth")


def test_social_callback_creates_user_and_returns_jwt(session):
    payload = SocialLogin(provider="google", token="dummy")
    with patch("routers.auth.emit_event"):
        result = social_callback(payload, BackgroundTasks(), db=session)
    assert "access_token" in result
    user = session.query(User).filter_by(provider="google").first()
    assert user is not None
    decoded = jwt_service.decode_token(result["access_token"])
    assert decoded["sub"] == str(user.id)
    assert decoded["email"] == user.email
    assert decoded["provider"] == "google"
