from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

_engine: Engine | None = None
SessionLocal: sessionmaker[Session] | None = None


def init_engine(database_url: str | None = None) -> Engine:
    global _engine, SessionLocal

    settings = get_settings()
    url = database_url or settings.database_url

    _engine = create_engine(url, pool_pre_ping=True)
    SessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False, expire_on_commit=False)
    return _engine


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        _engine = init_engine()
    return _engine


def get_db_session() -> Generator[Session, None, None]:
    global SessionLocal
    if SessionLocal is None:
        init_engine()

    assert SessionLocal is not None
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
