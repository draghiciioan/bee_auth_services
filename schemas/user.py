from __future__ import annotations

import re
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator, ConfigDict

from utils.settings import settings

from models.user import UserRole

PASSWORD_REGEX = re.compile(settings.password_regex)
PHONE_REGEX = re.compile(r"^\+[1-9]\d{1,14}$")


class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None
    phone_number: Optional[str] = Field(
        default=None, pattern=PHONE_REGEX.pattern
    )
    role: UserRole = UserRole.CLIENT


class UserCreate(UserBase):
    password: str

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if not PASSWORD_REGEX.match(v):
            raise ValueError(
                "Password must be at least 8 characters long and include one uppercase letter, one digit, and one special character"
            )
        return v


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserRead(UserBase):
    id: UUID

    model_config = ConfigDict(from_attributes=True)


class SocialLogin(BaseModel):
    provider: str
    token: str


class TwoFAVerify(BaseModel):
    twofa_token: str


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordReset(BaseModel):
    token: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if not PASSWORD_REGEX.match(v):
            raise ValueError(
                "Password must be at least 8 characters long and include one uppercase letter, one digit, and one special character"
            )
        return v


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str
