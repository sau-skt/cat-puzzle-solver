"""Database engine and session factory.

The engine is created lazily so tests can point DATABASE_URL at SQLite
before the first connection.
"""

from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings

_engine: Engine | None = None
_engine_url: str | None = None
_session_factory: sessionmaker[Session] | None = None


def _build_engine(url: str) -> Engine:
    kwargs: dict = {"future": True}
    if url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
        if url in {"sqlite://", "sqlite:///:memory:"}:
            kwargs["poolclass"] = StaticPool
    else:
        kwargs["pool_pre_ping"] = True
        kwargs["pool_recycle"] = 3600
        ca_path = get_settings().mysql_ssl_ca_path
        if ca_path:
            kwargs["connect_args"] = {"ssl": {"ca": ca_path}}
    engine = create_engine(url, **kwargs)

    @event.listens_for(engine, "connect")
    def _enable_sqlite_fk(dbapi_connection, _connection_record) -> None:  # type: ignore[no-untyped-def]
        module = getattr(dbapi_connection.__class__, "__module__", "")
        if module.startswith("sqlite3"):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


def get_engine() -> Engine:
    global _engine, _engine_url, _session_factory
    url = get_settings().database_url
    if _engine is None or _engine_url != url:
        if _engine is not None:
            _engine.dispose()
        _engine = _build_engine(url)
        _engine_url = url
        _session_factory = sessionmaker(bind=_engine, autoflush=False, expire_on_commit=False)
    return _engine


def get_sessionmaker() -> sessionmaker[Session]:
    get_engine()
    assert _session_factory is not None
    return _session_factory


def get_db() -> Generator[Session, None, None]:
    db = get_sessionmaker()()
    try:
        yield db
    finally:
        db.close()


def reset_engine() -> None:
    """Dispose the cached engine. Used by tests after changing DATABASE_URL."""
    global _engine, _engine_url, _session_factory
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _engine_url = None
    _session_factory = None
