import pytest
import importlib
from pydantic import ValidationError

from schemas.user import UserCreate
from models.user import UserRole


def test_password_strength_ok():
    data = {
        "email": "test@example.com",
        "password": "Strong1!",
    }
    user = UserCreate(**data)
    assert user.password == data["password"]


def test_password_strength_fail():
    with pytest.raises(ValidationError):
        UserCreate(email="a@b.com", password="weak")


def test_phone_number_format():
    user = UserCreate(
        email="c@d.com",
        password="Valid1@A",
        phone_number="+40721234567",
    )
    assert user.phone_number == "+40721234567"


def test_role_assignment():
    user = UserCreate(
        email="r@r.com",
        password="Valid1@A",
        role=UserRole.ADMIN_BUSINESS,
    )
    assert user.role is UserRole.ADMIN_BUSINESS


def test_custom_password_regex(monkeypatch):
    monkeypatch.setenv("PASSWORD_REGEX", r"^\d{4}$")

    import settings as settings_mod
    settings_mod = importlib.reload(settings_mod)
    import schemas.user as user_mod
    user_mod = importlib.reload(user_mod)

    user = user_mod.UserCreate(email="c@example.com", password="1234")
    assert user.password == "1234"

    monkeypatch.delenv("PASSWORD_REGEX", raising=False)
    importlib.reload(settings_mod)
    importlib.reload(user_mod)


def test_custom_password_regex_fail(monkeypatch):
    monkeypatch.setenv("PASSWORD_REGEX", r"^\d{4}$")

    import settings as settings_mod
    settings_mod = importlib.reload(settings_mod)
    import schemas.user as user_mod
    user_mod = importlib.reload(user_mod)

    with pytest.raises(ValidationError):
        user_mod.UserCreate(email="d@example.com", password="abcd")

    monkeypatch.delenv("PASSWORD_REGEX", raising=False)
    importlib.reload(settings_mod)
    importlib.reload(user_mod)
