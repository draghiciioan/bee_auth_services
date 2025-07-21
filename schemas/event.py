from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class BaseEvent(BaseModel):
    """Base fields shared by all events."""

    event_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    user_id: uuid.UUID
    email: Optional[EmailStr] = None
    provider: Optional[str] = None


class UserRegisteredEvent(BaseEvent):
    """Emitted when a new user registers."""


class UserLoggedInEvent(BaseEvent):
    """Emitted when a user successfully logs in."""


class TwoFARequestedEvent(BaseEvent):
    """Emitted when a user requests a 2FA code."""


class EmailVerificationSentEvent(BaseEvent):
    """Emitted when a verification email is sent to the user."""

