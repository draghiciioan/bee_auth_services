import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import Boolean, Column, DateTime, Enum as PgEnum, String
from sqlalchemy.dialects.postgresql import UUID

from database import Base


class UserRole(str, Enum):
    CLIENT = "client"
    ADMIN_BUSINESS = "admin_business"
    COURIER = "courier"
    COLLABORATOR = "collaborator"
    SUPERADMIN = "superadmin"


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String)
    phone_number = Column(String)
    role = Column(PgEnum(UserRole), nullable=False, default=UserRole.CLIENT)
    is_active = Column(Boolean, default=True)
    is_email_verified = Column(Boolean, default=False)
    is_social = Column(Boolean, default=False)
    provider = Column(String)
    social_id = Column(String)
    avatar_url = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )
