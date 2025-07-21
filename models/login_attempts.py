import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Index
from sqlalchemy.dialects.postgresql import UUID

from database import Base


class LoginAttempt(Base):
    __tablename__ = "login_attempts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
    )
    email_attempted = Column(String(255), nullable=False)
    ip_address = Column(String, nullable=False)
    user_agent = Column(String)
    success = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("ix_login_attempts_user_id_created_at", "user_id", "created_at"),
    )
