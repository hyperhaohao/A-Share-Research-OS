"""Database engine/session plumbing (SQLAlchemy 2).

Development runs on file SQLite (``ASRO_DATABASE_URL`` override supported);
the production target is PostgreSQL (任务书 §5). Schema changes must go
through Alembic migrations — ``create_all`` is only used for tests.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings

_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        _engine = make_engine()
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    global _session_factory
    if _session_factory is None:
        _session_factory = make_session_factory(get_engine())
    return _session_factory


def get_session() -> Iterator[Session]:
    """FastAPI dependency: one session per request."""
    with session_scope(get_session_factory()) as session:
        yield session


def reset_engine() -> None:
    """Test seam."""
    global _engine, _session_factory
    _engine = None
    _session_factory = None


def make_engine(database_url: str | None = None) -> Engine:
    url = database_url or get_settings().database_url
    engine = create_engine(url, future=True)
    if url.startswith("sqlite"):
        @event.listens_for(engine, "connect")
        def _set_sqlite_pragma(dbapi_connection, _record):  # noqa: ANN001
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.close()
    return engine


def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, future=True, expire_on_commit=False)


@contextmanager
def session_scope(factory: sessionmaker[Session]) -> Iterator[Session]:
    """Transactional scope: commit on success, rollback on error."""
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
