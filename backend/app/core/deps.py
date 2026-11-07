"""Request dependencies for database access and the authenticated user."""

from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import decode_access_token
from app.database.session import get_db
from app.models.types import utcnow
from app.models.user import User, UserSession

DbSession = Annotated[Session, Depends(get_db)]


def get_current_user(request: Request, db: DbSession) -> User:
    settings = get_settings()
    token = request.cookies.get(settings.cookie_name)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required.")
    try:
        payload = decode_access_token(token)
    except jwt.PyJWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required.")
    user_id = payload.get("sub")
    session_id = payload.get("jti")
    if not user_id or not session_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required.")
    session = db.get(UserSession, session_id)
    if session is None or session.user_id != user_id or session.revoked_at is not None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required.")
    if session.expires_at <= utcnow():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired.")
    user = db.scalar(select(User).where(User.id == user_id, User.is_active.is_(True)))
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required.")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_verified_user(user: CurrentUser) -> User:
    settings = get_settings()
    if settings.require_email_verification and not user.is_verified:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Verify your email before continuing.")
    return user


VerifiedUser = Annotated[User, Depends(require_verified_user)]
