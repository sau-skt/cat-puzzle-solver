"""Signup, session cookies, and password recovery."""

import logging
import secrets
from datetime import timedelta

from fastapi import HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.rate_limit import clear_login_failures, ensure_login_allowed, record_login_failure
from app.core.security import (
    clear_auth_cookie,
    create_access_token,
    decode_access_token,
    digest_token,
    dummy_password_hash,
    hash_password,
    set_auth_cookie,
    tokens_match,
    verify_password,
)
from app.models.types import utcnow
from app.models.user import PasswordResetToken, User, UserSession
from app.schemas.auth import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    MessageResponse,
    ProfileUpdate,
    ResetPasswordRequest,
    SignupRequest,
    UserResponse,
    VerifyEmailRequest,
)
from app.services.email_service import send_email

logger = logging.getLogger("catpuzzle.auth")


def signup(db: Session, payload: SignupRequest, response: Response) -> UserResponse:
    settings = get_settings()
    if db.scalar(select(User).where(User.email == payload.email)):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="An account with that email already exists.")
    phone_e164 = f"{payload.dial_code}{payload.phone_number}"
    if db.scalar(select(User).where(User.phone_e164 == phone_e164)):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="An account with that phone number already exists.")
    user = User(
        full_name=payload.full_name,
        email=payload.email,
        country_iso=payload.country_iso,
        dial_code=payload.dial_code,
        phone_number=payload.phone_number,
        phone_e164=phone_e164,
        password_hash=hash_password(payload.password),
        is_verified=not settings.require_email_verification,
    )
    verification_token = None
    if settings.require_email_verification:
        verification_token = secrets.token_urlsafe(32)
        user.verification_token_hash = digest_token(verification_token)
        user.verification_expires = utcnow() + timedelta(hours=24)
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with that email or phone number already exists.",
        )
    db.refresh(user)
    if verification_token:
        link = f"{settings.app_public_url}/verify-email?token={verification_token}"
        send_email(
            user.email,
            "Verify your Cat Puzzle Solver account",
            f"Hello {user.full_name},\n\nConfirm your email by opening this link:\n{link}\n\nThe link expires in 24 hours.\n",
        )
    else:
        _issue_session(db, user, response, remember_me=False, user_agent=None)
    logger.info("Created account %s", user.id)
    return UserResponse.model_validate(user)


def login(db: Session, payload: LoginRequest, response: Response, request: Request) -> UserResponse:
    key = payload.email
    ensure_login_allowed(key)
    user = db.scalar(select(User).where(User.email == payload.email))
    password_hash = user.password_hash if user else dummy_password_hash()
    valid = verify_password(password_hash, payload.password)
    if user is None or not valid:
        record_login_failure(key)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password.")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This account is disabled.")
    settings = get_settings()
    if settings.require_email_verification and not user.is_verified:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Verify your email before logging in.")
    clear_login_failures(key)
    _issue_session(db, user, response, payload.remember_me, request.headers.get("user-agent"))
    logger.info("Login succeeded for %s", user.id)
    return UserResponse.model_validate(user)


def logout(db: Session, request: Request, response: Response) -> None:
    settings = get_settings()
    token = request.cookies.get(settings.cookie_name)
    if token:
        try:
            payload = decode_access_token(token)
            session = db.get(UserSession, payload.get("jti"))
            if session and session.revoked_at is None:
                session.revoked_at = utcnow()
                db.commit()
        except Exception:
            db.rollback()
    clear_auth_cookie(response)


def forgot_password(db: Session, payload: ForgotPasswordRequest, request: Request) -> MessageResponse:
    settings = get_settings()
    message = "If that email is registered, a password reset link has been sent."
    user = db.scalar(select(User).where(User.email == payload.email))
    raw_token = None
    if user and user.is_active:
        raw_token = secrets.token_urlsafe(32)
        db.add(
            PasswordResetToken(
                user_id=user.id,
                token_hash=digest_token(raw_token),
                expires_at=utcnow() + timedelta(minutes=30),
                request_ip=_client_ip(request),
            )
        )
        db.commit()
        link = f"{settings.app_public_url}/reset-password?token={raw_token}"
        send_email(
            user.email,
            "Reset your Cat Puzzle Solver password",
            f"Hello {user.full_name},\n\nReset your password with this link:\n{link}\n\nThe link expires in 30 minutes. If you did not ask for this, ignore the email.\n",
        )
    return MessageResponse(message=message, reset_token=raw_token if settings.debug_return_tokens else None)


def reset_password(db: Session, payload: ResetPasswordRequest) -> MessageResponse:
    token_hash = digest_token(payload.token)
    record = db.scalar(select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash))
    if record is None or record.used_at is not None or record.expires_at <= utcnow():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This reset link is invalid or expired.")
    user = db.get(User, record.user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This reset link is invalid or expired.")
    user.password_hash = hash_password(payload.password)
    user.updated_at = utcnow()
    record.used_at = utcnow()
    _revoke_all_sessions(db, user.id)
    db.commit()
    logger.info("Password reset for %s", user.id)
    return MessageResponse(message="Password updated. You can log in with the new password.")


def verify_email(db: Session, payload: VerifyEmailRequest) -> MessageResponse:
    token_hash = digest_token(payload.token)
    user = db.scalar(select(User).where(User.verification_token_hash == token_hash))
    if user is None or user.verification_expires is None or user.verification_expires <= utcnow():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This verification link is invalid or expired.")
    user.is_verified = True
    user.verification_token_hash = None
    user.verification_expires = None
    user.updated_at = utcnow()
    db.commit()
    return MessageResponse(message="Email verified. You can log in.")


def update_profile(db: Session, user: User, payload: ProfileUpdate) -> UserResponse:
    user.full_name = payload.full_name
    user.updated_at = utcnow()
    db.commit()
    db.refresh(user)
    return UserResponse.model_validate(user)


def change_password(
    db: Session,
    user: User,
    payload: ChangePasswordRequest,
    response: Response,
    request: Request,
) -> MessageResponse:
    if not verify_password(user.password_hash, payload.current_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect.")
    user.password_hash = hash_password(payload.password)
    user.updated_at = utcnow()
    _revoke_all_sessions(db, user.id)
    db.commit()
    _issue_session(db, user, response, remember_me=False, user_agent=request.headers.get("user-agent"))
    return MessageResponse(message="Password updated.")


def _issue_session(db: Session, user: User, response: Response, remember_me: bool, user_agent: str | None) -> None:
    settings = get_settings()
    minutes = settings.remember_me_expire_minutes if remember_me else settings.access_token_expire_minutes
    session = UserSession(
        user_id=user.id,
        expires_at=utcnow() + timedelta(minutes=minutes),
        remember_me=remember_me,
        user_agent=(user_agent or "")[:255] or None,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    token = create_access_token(user.id, session.id, minutes)
    set_auth_cookie(response, token, minutes * 60)


def _revoke_all_sessions(db: Session, user_id: str) -> None:
    sessions = db.scalars(select(UserSession).where(UserSession.user_id == user_id, UserSession.revoked_at.is_(None))).all()
    now = utcnow()
    for session in sessions:
        session.revoked_at = now


def _client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()[:64]
    if request.client:
        return request.client.host
    return None
