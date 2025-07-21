from __future__ import annotations

import os
import warnings
from passlib.hash import bcrypt


warnings.filterwarnings("ignore", "'crypt' is deprecated", DeprecationWarning)

# Configuration loaded from environment variables
SECRET_KEY = os.getenv("SECRET_KEY", "secret")
ALGORITHM = "HS256"
TOKEN_EXPIRATION_SECONDS = int(os.getenv("TOKEN_EXPIRATION_SECONDS", "7200"))


def hash_password(password: str) -> str:
    """Hash a plain password using bcrypt."""
    return bcrypt.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    """Verify a password against its bcrypt hash."""
    return bcrypt.verify(password, hashed_password)


