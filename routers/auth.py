from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordBearer
from fastapi_limiter.depends import RateLimiter
from sqlalchemy.orm import Session

from database import SessionLocal
from models import EmailVerification, TwoFAToken, User
from schemas.user import (
    SocialLogin,
    TwoFAVerify,
    UserCreate,
    UserLogin,
    UserRead,
)
from services import auth as auth_service
from services import jwt as jwt_service
from utils import hash_password, verify_password
from events.rabbitmq import emit_event
from schemas.event import (
    EmailVerificationSentEvent,
    TwoFARequestedEvent,
    UserLoggedInEvent,
    UserRegisteredEvent,
)

router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post(
    "/register",
    response_model=UserRead,
    dependencies=[Depends(RateLimiter(times=5, seconds=60))],
)
def register(
    user_in: UserCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    if db.query(User).filter_by(email=user_in.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
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

    auth_service.create_email_verification(db, user)
    background_tasks.add_task(
        emit_event,
        "user.registered",
        UserRegisteredEvent(user_id=user.id, email=user.email).dict(),
    )
    background_tasks.add_task(
        emit_event,
        "user.email_verification_sent",
        EmailVerificationSentEvent(user_id=user.id, email=user.email).dict(),
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
    dependencies=[Depends(RateLimiter(times=5, seconds=60))],
)
def login(
    request: Request,
    credentials: UserLogin,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    user = db.query(User).filter_by(email=credentials.email).first()
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
        raise HTTPException(status_code=400, detail="Invalid credentials")

    auth_service.record_login_attempt(
        db,
        user.id,
        request,
        True,
        credentials.email,
    )

    if not user.is_email_verified:
        raise HTTPException(status_code=400, detail="Email not verified")

    if user.phone_number:
        token = auth_service.create_twofa_token(db, user)
        background_tasks.add_task(
            emit_event,
            "user.2fa_requested",
            TwoFARequestedEvent(
                user_id=user.id,
                email=user.email,
                provider=user.provider or "local",
            ).dict(),
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
        ).dict(),
    )
    return {"access_token": jwt_token, "token_type": "bearer"}


@router.get("/auth/social/login")
def social_login(provider: str):
    # Placeholder for OAuth login URL generation
    return {"login_url": f"https://{provider}.com/oauth"}


@router.post("/auth/social/callback")
def social_callback(
    payload: SocialLogin,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    # Placeholder for OAuth callback handling
    email = f"user_{payload.provider}@example.com"
    user = db.query(User).filter_by(email=email).first()
    if not user:
        user = User(
            email=email,
            hashed_password="",
            is_social=True,
            provider=payload.provider,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    jwt_token = jwt_service.create_token(
        user_id=str(user.id),
        email=user.email,
        role=user.role.value,
        provider=user.provider or payload.provider,
    )
    background_tasks.add_task(
        emit_event,
        "user.logged_in",
        UserLoggedInEvent(
            user_id=user.id,
            email=user.email,
            provider=user.provider or payload.provider,
        ).dict(),
    )
    return {"access_token": jwt_token, "token_type": "bearer"}


@router.get("/verify-email")
def verify_email(token: str, db: Session = Depends(get_db)):
    record = (
        db.query(EmailVerification)
        .filter_by(token=token)
        .filter(EmailVerification.expires_at > datetime.utcnow())
        .first()
    )
    if not record:
        raise HTTPException(status_code=400, detail="Invalid token")
    user = db.query(User).get(record.user_id)
    user.is_email_verified = True
    db.delete(record)
    db.commit()
    return {"message": "email_verified"}


@router.post("/verify-2fa")
def verify_twofa(
    payload: TwoFAVerify,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    token = (
        db.query(TwoFAToken)
        .filter_by(token=payload.twofa_token, is_used=False)
        .filter(TwoFAToken.expires_at > datetime.utcnow())
        .first()
    )
    if not token:
        raise HTTPException(status_code=400, detail="Invalid token")
    user = db.query(User).get(token.user_id)
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
        ).dict(),
    )
    return {"access_token": jwt_token, "token_type": "bearer"}


@router.get("/validate", dependencies=[Depends(RateLimiter(times=100, seconds=60))])
def validate(token: str = Depends(oauth2_scheme)):
    """Validate a JWT and return standardized response."""
    try:
        payload = jwt_service.decode_token(token)
    except Exception as exc:
        return JSONResponse(status_code=401, content={"valid": False, "error": str(exc)})
    return {
        "valid": True,
        "user_id": payload["sub"],
        "email": payload["email"],
        "role": payload["role"],
        "provider": payload.get("provider", "local"),
    }


@router.get("/me", response_model=UserRead)
def me(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    payload = jwt_service.decode_token(token)
    user = db.query(User).get(payload["sub"])
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserRead(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        phone_number=user.phone_number,
        role=user.role,
    )
