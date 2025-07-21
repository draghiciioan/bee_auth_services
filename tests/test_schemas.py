import pytest
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
