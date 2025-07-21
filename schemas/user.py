from __future__ import annotations

import re
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, validator

from models.user import UserRole

PASSWORD_REGEX = re.compile(r"^(?=.*[A-Z])(?=.*\d)(?=.*[^\w\s]).{8,}$")
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

    @validator("password")
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

    class Config:
        orm_mode = True


class SocialLogin(BaseModel):
    provider: str
    token: str


class TwoFAVerify(BaseModel):
    twofa_token: str
