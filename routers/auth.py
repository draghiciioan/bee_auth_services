from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from database import SessionLocal
from models import (
    EmailVerification,
    LoginAttempt,
    TwoFAToken,
    User,
    UserRole,
)
from services import auth as auth_service
from services import jwt as jwt_service

router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/register")
def register(
    email: str,
    password: str,
    full_name: Optional[str] = None,
    phone_number: Optional[str] = None,
    db: Session = Depends(get_db),
):
    if db.query(User).filter_by(email=email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    hashed = auth_service.hash_password(password)
    user = User(
        email=email,
        hashed_password=hashed,
        full_name=full_name,
        phone_number=phone_number,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = auth_service.create_email_verification(db, user)
    return {"message": "registered", "email_token": token.token}


@router.post("/login")
def login(
    request: Request,
    email: str,
    password: str,
    db: Session = Depends(get_db),
):
    user = db.query(User).filter_by(email=email).first()
    if not user or not auth_service.verify_password(password, user.hashed_password):
        auth_service.record_login_attempt(db, user.id if user else None, request, False)
        raise HTTPException(status_code=400, detail="Invalid credentials")

    auth_service.record_login_attempt(db, user.id, request, True)

    if not user.is_email_verified:
        raise HTTPException(status_code=400, detail="Email not verified")

    if user.phone_number:
        token = auth_service.create_twofa_token(db, user)
        return {"message": "2fa_required", "twofa_token": token.token}

    jwt = jwt_service.create_token({"sub": str(user.id), "role": user.role.value})
    return {"access_token": jwt, "token_type": "bearer"}


@router.get("/auth/social/login")
def social_login(provider: str):
    # Placeholder for OAuth login URL generation
    return {"login_url": f"https://{provider}.com/oauth"}


@router.get("/auth/social/callback")
def social_callback(provider: str, token: str, db: Session = Depends(get_db)):
    # Placeholder for OAuth callback handling
    email = f"user_{provider}@example.com"
    user = db.query(User).filter_by(email=email).first()
    if not user:
        user = User(email=email, hashed_password="", is_social=True, provider=provider)
        db.add(user)
        db.commit()
        db.refresh(user)
    jwt = jwt_service.create_token({"sub": str(user.id), "role": user.role.value})
    return {"access_token": jwt, "token_type": "bearer"}


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
def verify_twofa(twofa_token: str, db: Session = Depends(get_db)):
    token = (
        db.query(TwoFAToken)
        .filter_by(token=twofa_token, is_used=False)
        .filter(TwoFAToken.expires_at > datetime.utcnow())
        .first()
    )
    if not token:
        raise HTTPException(status_code=400, detail="Invalid token")
    user = db.query(User).get(token.user_id)
    jwt = jwt_service.create_token({"sub": str(user.id), "role": user.role.value})
    token.is_used = True
    db.commit()
    return {"access_token": jwt, "token_type": "bearer"}


@router.get("/validate")
def validate(token: str = Depends(oauth2_scheme)):
    payload = jwt_service.decode_token(token)
    return payload


@router.get("/me")
def me(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    payload = jwt_service.decode_token(token)
    user = db.query(User).get(payload["sub"])
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "id": str(user.id),
        "email": user.email,
        "role": user.role.value,
        "full_name": user.full_name,
    }
