"""Process-local login throttling.

A single Uvicorn worker enforces this limit. Put a shared store in front of
multiple workers before relying on it in a scaled deployment.
"""

from __future__ import annotations

import time

from fastapi import HTTPException, status

from app.core.config import get_settings

_failures: dict[str, list[float]] = {}


def reset_login_limits() -> None:
    _failures.clear()


def record_login_failure(key: str) -> None:
    settings = get_settings()
    now = time.monotonic()
    window = settings.login_window_seconds
    recent = [stamp for stamp in _failures.get(key, []) if now - stamp < window]
    recent.append(now)
    _failures[key] = recent


def ensure_login_allowed(key: str) -> None:
    settings = get_settings()
    now = time.monotonic()
    window = settings.login_window_seconds
    recent = [stamp for stamp in _failures.get(key, []) if now - stamp < window]
    _failures[key] = recent
    if len(recent) >= settings.login_max_attempts:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Try again later.",
        )


def clear_login_failures(key: str) -> None:
    _failures.pop(key, None)
