from datetime import datetime, timedelta, timezone
import secrets
import pyotp

from fastapi import Request
from sqlalchemy.orm import Session

from utils.settings import settings
from utils import twofa_token_generated_counter

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


def failed_attempts_count(db: Session, email: str) -> int:
    """Return the number of failed login attempts for an email in the current window."""
    since = datetime.now(timezone.utc) - timedelta(
        seconds=settings.login_attempt_window_seconds
    )
    return (
        db.query(LoginAttempt)
        .filter_by(email_attempted=email, success=False)
        .filter(LoginAttempt.created_at >= since)
        .count()
    )


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
) -> int:
    attempt = LoginAttempt(
        user_id=user_id,
        email_attempted=email_attempted,
        ip_address=request.client.host,
        user_agent=request.headers.get("user-agent", ""),
        success=success,
    )
    db.add(attempt)
    db.commit()

    if not success:
        since = datetime.now(timezone.utc) - timedelta(
            seconds=settings.login_attempt_window_seconds
        )
        return (
            db.query(LoginAttempt)
            .filter_by(email_attempted=email_attempted, success=False)
            .filter(LoginAttempt.created_at >= since)
            .count()
        )
    return 0

def create_twofa_token(db: Session, user: User) -> TwoFAToken:
    """Generate a longer random token for two-factor authentication."""
    # 12 hexadecimal characters provide 48 bits of entropy
    token = secrets.token_hex(6)
    expires = datetime.now(timezone.utc) + timedelta(minutes=TWOFA_EXPIRATION_MINUTES)
    record = TwoFAToken(user_id=user.id, token=token, expires_at=expires)
    db.add(record)
    db.commit()
    db.refresh(record)
    twofa_token_generated_counter.inc()
    return record


def generate_totp_secret() -> str:
    """Return a new base32 secret for TOTP."""
    return pyotp.random_base32()


def verify_totp(user: User, code: str) -> bool:
    """Verify a TOTP code against a user's secret."""
    if not user.totp_secret:
        return False
    totp = pyotp.TOTP(user.totp_secret)
    return totp.verify(code, valid_window=1)


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
