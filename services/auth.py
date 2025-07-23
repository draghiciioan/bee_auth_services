from datetime import datetime, timedelta, timezone
import secrets

from fastapi import Request
from sqlalchemy.orm import Session

from models import (
    EmailVerification,
    LoginAttempt,
    TwoFAToken,
    User,
    PasswordResetToken,
)

EMAIL_TOKEN_EXPIRATION_MINUTES = 15
TWOFA_EXPIRATION_MINUTES = 5
PASSWORD_RESET_EXPIRATION_MINUTES = 30


def create_email_verification(db: Session, user: User) -> EmailVerification:
    token = secrets.token_urlsafe(32)
    expires = datetime.now(timezone.utc) + timedelta(minutes=EMAIL_TOKEN_EXPIRATION_MINUTES)
    record = EmailVerification(user_id=user.id, token=token, expires_at=expires)
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def record_login_attempt(
    db: Session,
    user_id: str | None,
    request: Request,
    success: bool,
    email_attempted: str,
) -> None:
    attempt = LoginAttempt(
        user_id=user_id,
        email_attempted=email_attempted,
        ip_address=request.client.host,
        user_agent=request.headers.get("user-agent", ""),
        success=success,
    )
    db.add(attempt)
    db.commit()


def create_twofa_token(db: Session, user: User) -> TwoFAToken:
    """Generate a longer random token for two-factor authentication."""
    # 12 hexadecimal characters provide 48 bits of entropy
    token = secrets.token_hex(6)
    expires = datetime.now(timezone.utc) + timedelta(minutes=TWOFA_EXPIRATION_MINUTES)
    record = TwoFAToken(user_id=user.id, token=token, expires_at=expires)
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def create_password_reset_token(
    db: Session, user: User
) -> PasswordResetToken:
    token = secrets.token_urlsafe(32)
    expires = datetime.now(timezone.utc) + timedelta(
        minutes=PASSWORD_RESET_EXPIRATION_MINUTES
    )
    record = PasswordResetToken(
        user_id=user.id, token=token, expires_at=expires
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def validate_password_reset_token(
    db: Session, token: str
) -> PasswordResetToken | None:
    return (
        db.query(PasswordResetToken)
        .filter_by(token=token, used=False)
        .filter(PasswordResetToken.expires_at > datetime.now(timezone.utc))
        .first()
    )
