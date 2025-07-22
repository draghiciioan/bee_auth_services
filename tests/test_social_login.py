import asyncio
from unittest.mock import ANY, patch

from fastapi import BackgroundTasks
from models import User
from routers.auth import social_callback, social_login
from schemas.user import SocialLogin
from services import jwt as jwt_service


def test_social_login_url_generation(monkeypatch):
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "id")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "secret")
    monkeypatch.setenv("GOOGLE_REDIRECT_URI", "http://localhost")
    response = social_login("google")
    assert "accounts.google.com" in response["login_url"]


def test_social_callback_creates_user_and_returns_jwt(session):
    payload = SocialLogin(provider="google", token="dummy")
    bg = BackgroundTasks()
    with patch("events.rabbitmq.emit_event") as emit_mock, patch(
        "routers.auth.emit_event", emit_mock
    ), patch("services.social.fetch_user_info") as fetch_mock:
        fetch_mock.return_value = {
            "email": "social@example.com",
            "social_id": "123",
            "avatar_url": "http://avatar",
            "full_name": "Social User",
        }
        result = social_callback(payload, bg, db=session)
        asyncio.run(bg())
    assert "access_token" in result
    user = session.query(User).filter_by(provider="google").first()
    assert user is not None
    decoded = jwt_service.decode_token(result["access_token"])
    assert decoded["sub"] == str(user.id)
    assert decoded["email"] == user.email
    assert decoded["provider"] == "google"
    emit_mock.assert_called_once_with(
        "user.logged_in",
        {
            "event_id": ANY,
            "timestamp": ANY,
            "user_id": user.id,
            "email": user.email,
            "provider": "google",
        },
    )
