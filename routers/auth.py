from datetime import datetime, timezone
import uuid
import time

from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
import logging
import pyotp
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordBearer
from fastapi_limiter.depends import RateLimiter
from utils.rate_limit import user_rate_limit_key
from sqlalchemy.orm import Session

from database import SessionLocal
from models import EmailVerification, TwoFAToken, User
from schemas.user import (
    SocialLogin,
    TwoFAVerify,
    UserCreate,
    UserLogin,
    UserRead,
    PasswordResetRequest,
    PasswordReset,
    RefreshTokenRequest,
    LogoutRequest,
)
from services import auth as auth_service
from services import jwt as jwt_service
from services import social as social_service
from utils.settings import settings
from utils import (
    hash_password,
    verify_password,
    login_success_counter,
    register_failed_counter,
    user_registration_counter,
    authentication_latency,
    password_reset_requested_counter,
)
from utils.errors import ErrorCode
from events.rabbitmq import emit_event
from schemas.event import (
    EmailVerificationSentEvent,
    TwoFARequestedEvent,
    UserLoggedInEvent,
    UserRegisteredEvent,
)

router = APIRouter(prefix="/v1/auth")
logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/v1/auth/login")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post(
    "/register",
    response_model=UserRead,
    summary="Register new user",
    description="Create a new user account and send email verification.",
    # Limit registration attempts per user identifier/IP
    dependencies=[Depends(RateLimiter(times=5, seconds=60, identifier=user_rate_limit_key))],
)
def register(
    user_in: UserCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    if db.query(User).filter_by(email=user_in.email).first():
        register_failed_counter.inc()
        logger.warning(
            "register_failed",
            extra={"endpoint": "/register", "user_id": None, "ip": None},
        )
        raise HTTPException(
            status_code=400,
            detail={
                "code": ErrorCode.EMAIL_ALREADY_REGISTERED,
                "message": "Email already registered",
            },
        )
    hashed = hash_password(user_in.password)
    user = User(
        email=user_in.email,
        hashed_password=hashed,
        full_name=user_in.full_name,
        phone_number=user_in.phone_number,
        role=user_in.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Increment registrations counter by provider
    user_registration_counter.labels(provider="local").inc()

    auth_service.create_email_verification(db, user)
    background_tasks.add_task(
        emit_event,
        "user.registered",
        UserRegisteredEvent(user_id=user.id, email=user.email).model_dump(),
    )
    background_tasks.add_task(
        emit_event,
        "user.email_verification_sent",
        EmailVerificationSentEvent(user_id=user.id, email=user.email).model_dump(),
    )
    return UserRead(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        phone_number=user.phone_number,
        role=user.role,
    )


@router.post(
    "/login",
    summary="User login",
    description="Authenticate user credentials and issue JWT.",
    # Apply per-user/IP rate limiting on login attempts
    dependencies=[Depends(RateLimiter(times=5, seconds=60, identifier=user_rate_limit_key))],
)
def login(
    request: Request,
    credentials: UserLogin,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    start_time = time.perf_counter()
    try:
        user = db.query(User).filter_by(email=credentials.email).first()

        failed_attempts = auth_service.failed_attempts_count(db, credentials.email)
        if failed_attempts >= settings.login_attempt_threshold:
            auth_service.record_login_attempt(
                db,
                user.id if user else None,
                request,
                False,
                credentials.email,
            )
            raise HTTPException(
                status_code=429,
                detail={
                    "code": ErrorCode.TOO_MANY_FAILED_ATTEMPTS,
                    "message": "Too many failed login attempts. Please try again later.",
                },
            )

        if not user or not verify_password(
            credentials.password, user.hashed_password
        ):
            auth_service.record_login_attempt(
                db,
                user.id if user else None,
                request,
                False,
                credentials.email,
            )
            failed_attempts = auth_service.failed_attempts_count(db, credentials.email)
            if failed_attempts >= settings.login_attempt_threshold:
                raise HTTPException(
                    status_code=429,
                    detail={
                        "code": ErrorCode.TOO_MANY_FAILED_ATTEMPTS,
                        "message": "Too many failed login attempts. Please try again later.",
                    },
                )
            raise HTTPException(
                status_code=400,
                detail={
                    "code": ErrorCode.INVALID_CREDENTIALS,
                    "message": "Invalid credentials",
                },
            )

        auth_service.record_login_attempt(
            db,
            user.id,
            request,
            True,
            credentials.email,
        )

        if not user.is_email_verified:
            raise HTTPException(
                status_code=400,
                detail={"code": ErrorCode.EMAIL_NOT_VERIFIED, "message": "Email not verified"},
            )

        if user.totp_secret or user.phone_number:
            token = auth_service.create_twofa_token(db, user)
            background_tasks.add_task(
                emit_event,
                "user.2fa_requested",
                TwoFARequestedEvent(
                    user_id=user.id,
                    email=user.email,
                    provider=user.provider or "local",
                ).model_dump(),
            )
            return {"message": "2fa_required", "twofa_token": token.token}

        jwt_token = jwt_service.create_token(
            user_id=str(user.id),
            email=user.email,
            role=user.role.value,
            provider=user.provider or "local",
        )
        background_tasks.add_task(
            emit_event,
            "user.logged_in",
            UserLoggedInEvent(
                user_id=user.id,
                email=user.email,
                provider=user.provider or "local",
            ).model_dump(),
        )
        login_success_counter.inc()
        logger.info(
            "login_successful",
            extra={"endpoint": "/login", "user_id": user.id, "ip": request.client.host},
        )
        return {"access_token": jwt_token, "token_type": "bearer"}
    finally:
        authentication_latency.observe(time.perf_counter() - start_time)


@router.get(
    "/social/login",
    summary="Start OAuth login",
    description="Generate the provider authorization URL for social login.",
)
def social_login(provider: str):
    """Build provider authorization URL for OAuth login."""
    try:
        login_url = social_service.generate_login_url(provider)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail={
                "code": ErrorCode.UNSUPPORTED_PROVIDER,
                "message": "Unsupported provider",
            },
        )
    return {"login_url": login_url}


@router.post(
    "/social/callback",
    summary="OAuth callback",
    description="Handle provider callback, create or update user and issue JWT.",
)
def social_callback(
    payload: SocialLogin,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Exchange provider code for user info and return JWT."""
    try:
        info = social_service.fetch_user_info(payload.provider, payload.token)
    except Exception as exc:  # pragma: no cover - network errors
        raise HTTPException(
            status_code=400,
            detail={
                "code": ErrorCode.OAUTH_AUTH_FAILED,
                "message": "OAuth authentication failed",
            },
        ) from exc

    email = info.get("email")
    if not email:
        raise HTTPException(
            status_code=400,
            detail={"code": ErrorCode.EMAIL_NOT_AVAILABLE, "message": "Email not available"},
        )

    user = db.query(User).filter_by(email=email).first()
    if not user:
        user = User(
            email=email,
            hashed_password="",
            full_name=info.get("full_name"),
            avatar_url=info.get("avatar_url"),
            social_id=info.get("social_id"),
            is_social=True,
            provider=payload.provider,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        user_registration_counter.labels(provider=payload.provider).inc()
    else:
        user.full_name = user.full_name or info.get("full_name")
        user.avatar_url = info.get("avatar_url")
        user.social_id = info.get("social_id")
        user.provider = payload.provider
        db.commit()

    jwt_token = jwt_service.create_token(
        user_id=str(user.id),
        email=user.email,
        role=user.role.value,
        provider=user.provider,
    )
    background_tasks.add_task(
        emit_event,
        "user.logged_in",
        UserLoggedInEvent(
            user_id=user.id,
            email=user.email,
            provider=user.provider,
        ).model_dump(),
    )
    return {"access_token": jwt_token, "token_type": "bearer"}


@router.get(
    "/verify-email",
    summary="Verify email token",
    description="Validate email verification token and activate account.",
)
def verify_email(token: str, db: Session = Depends(get_db)):
    record = (
        db.query(EmailVerification)
        .filter_by(token=token)
        .filter(EmailVerification.expires_at > datetime.now(timezone.utc))
        .first()
    )
    if not record:
        raise HTTPException(
            status_code=400,
            detail={"code": ErrorCode.INVALID_TOKEN, "message": "Invalid token"},
        )
    user = db.get(User, record.user_id)
    user.is_email_verified = True
    db.delete(record)
    db.commit()
    return {"message": "email_verified"}


@router.post(
    "/verify-2fa",
    summary="Verify 2FA token",
    description="Validate two-factor authentication token and return JWT.",
    dependencies=[Depends(RateLimiter(times=5, seconds=60, identifier=user_rate_limit_key))],
)
def verify_twofa(
    payload: TwoFAVerify,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    twofa_token = payload.twofa_token.strip()
    token = (
        db.query(TwoFAToken)
        .filter_by(token=twofa_token, is_used=False)
        .filter(TwoFAToken.expires_at > datetime.now(timezone.utc))
        .first()
    )
    if not token:
        raise HTTPException(
            status_code=400,
            detail={"code": ErrorCode.INVALID_TOKEN, "message": "Invalid token"},
        )
    user = db.get(User, token.user_id)
    if user.totp_secret:
        totp_code = payload.totp_code.strip() if payload.totp_code else None
        if not totp_code or not auth_service.verify_totp(user, totp_code):
            raise HTTPException(
                status_code=400,
                detail={"code": ErrorCode.INVALID_TOKEN, "message": "Invalid token"},
            )
    jwt_token = jwt_service.create_token(
        user_id=str(user.id),
        email=user.email,
        role=user.role.value,
        provider=user.provider or "local",
    )
    token.is_used = True
    db.commit()
    background_tasks.add_task(
        emit_event,
        "user.logged_in",
        UserLoggedInEvent(
            user_id=user.id,
            email=user.email,
            provider=user.provider or "local",
        ).model_dump(),
    )
    login_success_counter.inc()
    return {"access_token": jwt_token, "token_type": "bearer"}


@router.post(
    "/request-reset",
    summary="Request password reset",
    description="Generate a password reset token and emit an event.",
    dependencies=[Depends(RateLimiter(times=3, seconds=300, identifier=user_rate_limit_key))],
)
def request_password_reset(
    payload: PasswordResetRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    user = db.query(User).filter_by(email=payload.email).first()
    if not user:
        raise HTTPException(
            status_code=404,
            detail={"code": ErrorCode.USER_NOT_FOUND, "message": "User not found"},
        )
    token = auth_service.create_password_reset_token(db, user)
    background_tasks.add_task(
        emit_event,
        "user.password_reset_requested",
        {
            "event_id": uuid.uuid4(),
            "timestamp": datetime.now(timezone.utc),
            "user_id": user.id,
            "email": user.email,
            "token": token.token,
        },
    )
    password_reset_requested_counter.inc()
    return {"message": "reset_requested"}


@router.post(
    "/reset-password",
    summary="Reset password",
    description="Validate password reset token and set new password.",
    dependencies=[Depends(RateLimiter(times=5, seconds=60, identifier=user_rate_limit_key))],
)
def reset_password(
    payload: PasswordReset,
    db: Session = Depends(get_db),
):
    token_value = payload.token.strip()
    record = auth_service.validate_password_reset_token(db, token_value)
    if not record:
        raise HTTPException(
            status_code=400,
            detail={"code": ErrorCode.INVALID_TOKEN, "message": "Invalid token"},
        )
    user = db.get(User, record.user_id)
    user.hashed_password = hash_password(payload.new_password)
    record.used = True
    db.commit()
    return {"message": "password_reset"}


@router.get(
    "/validate",
    summary="Validate JWT token",
    description="Check if a JWT is valid and return payload information.",
    # Higher rate limit for token validation endpoint
    dependencies=[Depends(RateLimiter(times=100, seconds=60, identifier=user_rate_limit_key))],
)
def validate(token: str = Depends(oauth2_scheme)):
    """Validate a JWT and return standardized response."""
    try:
        payload = jwt_service.decode_token(token)
        check_fn = getattr(jwt_service.jwt, "encode", None)
        if check_fn:
            regenerated = check_fn(
                payload,
                jwt_service.PRIVATE_KEY,
                algorithm=jwt_service.JWT_ALGORITHM,
            )
            if regenerated != token:
                raise ValueError("Invalid token")
    except Exception as exc:
        return JSONResponse(status_code=401, content={"valid": False, "error": str(exc)})
    return {
        "valid": True,
        "user_id": payload["sub"],
        "email": payload["email"],
        "role": payload["role"],
        "provider": payload.get("provider", "local"),
    }


@router.get(
    "/me",
    response_model=UserRead,
    summary="Current user info",
    description="Return details for the authenticated user based on JWT.",
)
def me(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    payload = jwt_service.decode_token(token)
    user_id = uuid.UUID(payload["sub"])
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=404,
            detail={"code": ErrorCode.USER_NOT_FOUND, "message": "User not found"},
        )
    return UserRead(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        phone_number=user.phone_number,
        role=user.role,
    )


@router.post(
    "/setup-2fa",
    summary="Generate TOTP secret",
    description=(
        "Create a TOTP secret for the authenticated user and return a provisioning URI."
    ),
)
def setup_twofa(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """Generate a new TOTP secret for a user and return provisioning URI."""
    payload = jwt_service.decode_token(token)
    user_id = uuid.UUID(payload["sub"])
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=404,
            detail={"code": ErrorCode.USER_NOT_FOUND, "message": "User not found"},
        )
    secret = auth_service.generate_totp_secret()
    user.totp_secret = secret
    db.commit()
    uri = pyotp.totp.TOTP(secret).provisioning_uri(
        name=user.email, issuer_name="BeeConect"
    )
    return {"provisioning_uri": uri}


@router.post("/refresh", summary="Refresh access token")
def refresh(payload: RefreshTokenRequest):
    try:
        info = jwt_service.decode_refresh_token(payload.refresh_token)
    except Exception:
        raise HTTPException(
            status_code=401,
            detail={"code": ErrorCode.INVALID_TOKEN, "message": "Invalid token"},
        )
    access = jwt_service.create_token(
        user_id=info["sub"],
        email=info["email"],
        role=info["role"],
        provider=info.get("provider", "local"),
    )
    return {"access_token": access, "token_type": "bearer"}


@router.post("/logout", summary="Logout user")
def logout(payload: LogoutRequest):
    try:
        jwt_service.revoke_refresh_token(payload.refresh_token)
    except Exception:
        pass
    return {"message": "logged_out"}
