from datetime import datetime, timedelta
import secrets
import hashlib

from fastapi import Request
from sqlalchemy.orm import Session

from models import EmailVerification, LoginAttempt, TwoFAToken, User

SALT_LENGTH = 16
EMAIL_TOKEN_EXPIRATION_MINUTES = 15
TWOFA_EXPIRATION_MINUTES = 5


def hash_password(password: str) -> str:
    salt = secrets.token_hex(SALT_LENGTH)
    dk = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), salt.encode(), 100_000
    ).hex()
    return f"{salt}${dk}"


def verify_password(password: str, hashed: str) -> bool:
    try:
        salt, dk = hashed.split("$")
    except ValueError:
        return False
    new_dk = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), salt.encode(), 100_000
    ).hex()
    return secrets.compare_digest(new_dk, dk)


def create_email_verification(db: Session, user: User) -> EmailVerification:
    token = secrets.token_urlsafe(32)
    expires = datetime.utcnow() + timedelta(minutes=EMAIL_TOKEN_EXPIRATION_MINUTES)
    record = EmailVerification(user_id=user.id, token=token, expires_at=expires)
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def record_login_attempt(
    db: Session, user_id: str | None, request: Request, success: bool
) -> None:
    attempt = LoginAttempt(
        user_id=user_id,
        ip_address=request.client.host,
        user_agent=request.headers.get("user-agent", ""),
        success=success,
    )
    db.add(attempt)
    db.commit()


def create_twofa_token(db: Session, user: User) -> TwoFAToken:
    token = secrets.token_hex(3)
    expires = datetime.utcnow() + timedelta(minutes=TWOFA_EXPIRATION_MINUTES)
    record = TwoFAToken(user_id=user.id, token=token, expires_at=expires)
    db.add(record)
    db.commit()
    db.refresh(record)
    return record
