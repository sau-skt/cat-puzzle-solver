"""Test environment. Forces SQLite so the suite never touches the development MySQL database."""

from __future__ import annotations

import os
import tempfile

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["JWT_SECRET"] = "test-jwt-secret-key-for-unit-tests-0123456789"
os.environ["DEBUG_RETURN_TOKENS"] = "true"
os.environ["REQUIRE_EMAIL_VERIFICATION"] = "false"
os.environ["COOKIE_SECURE"] = "false"
os.environ["STORAGE_DIR"] = tempfile.mkdtemp(prefix="catpuzzle-test-")
os.environ["SMTP_HOST"] = ""
os.environ["LOGIN_MAX_ATTEMPTS"] = "8"
os.environ["SOLVER_SOLUTION_LIMIT"] = "20"
os.environ["SOLVER_TIMEOUT_SECONDS"] = "8"

import pytest

from app.core.config import get_settings
from app.core.rate_limit import reset_login_limits
from app.database.base import Base
from app.database.session import get_engine, reset_engine
import app.models  # noqa: F401


@pytest.fixture(autouse=True)
def fresh_database():
    get_settings.cache_clear()
    reset_engine()
    reset_login_limits()
    engine = get_engine()
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield
    reset_engine()
    get_settings.cache_clear()


@pytest.fixture
def client(fresh_database):
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def strong_password() -> str:
    return "ValidPass1!"
