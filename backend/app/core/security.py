"""Password hashing, JWT cookies, and token digests."""

from __future__ import annotations

import hashlib
import hmac
import re
from datetime import datetime, timedelta, timezone
from functools import lru_cache

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import Response

from app.core.config import get_settings

_hasher = PasswordHasher()
_PASSWORD_RULES = (
    (r".{8,}", "Password must be at least 8 characters."),
    (r"[A-Z]", "Password must include an uppercase letter."),
    (r"[a-z]", "Password must include a lowercase letter."),
    (r"\d", "Password must include a digit."),
    (r"[^A-Za-z0-9]", "Password must include a symbol."),
)


def validate_password_strength(password: str) -> None:
    errors = [message for pattern, message in _PASSWORD_RULES if re.search(pattern, password) is None]
    if errors:
        raise ValueError(" ".join(errors))


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except VerifyMismatchError:
        return False
    except Exception:
        return False


@lru_cache
def dummy_password_hash() -> str:
    return _hasher.hash("not-a-real-password")


def digest_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def tokens_match(raw_token: str, token_hash: str) -> bool:
    return hmac.compare_digest(digest_token(raw_token), token_hash)


def create_access_token(user_id: str, session_id: str, expires_minutes: int) -> str:
    settings = get_settings()
    expire = datetime.now(timezone.utc) + timedelta(minutes=expires_minutes)
    payload = {"sub": user_id, "jti": session_id, "exp": expire, "iss": "cat-puzzle-solver"}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict:
    settings = get_settings()
    return jwt.decode(
        token,
        settings.jwt_secret,
        algorithms=[settings.jwt_algorithm],
        issuer="cat-puzzle-solver",
    )


def set_auth_cookie(response: Response, token: str, max_age_seconds: int) -> None:
    settings = get_settings()
    response.set_cookie(
        key=settings.cookie_name,
        value=token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,  # type: ignore[arg-type]
        max_age=max_age_seconds,
        path="/",
    )


def clear_auth_cookie(response: Response) -> None:
    settings = get_settings()
    response.delete_cookie(key=settings.cookie_name, path="/")
