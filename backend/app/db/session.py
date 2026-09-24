"""
Database engine, session factory, and FastAPI session dependency.

Architecture notes:
- Synchronous SQLAlchemy with psycopg2-binary driver.
- One Session per HTTP request via FastAPI's Depends(get_db).
- No global reusable Session instances.
- pool_pre_ping=True handles stale connections on managed PostgreSQL (Render).
- Engine is created lazily on first access so modules importing only the
  type annotations (e.g. during testing) do not require psycopg2 at import time.
"""

from __future__ import annotations

from collections.abc import Generator
from typing import TYPE_CHECKING

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.settings import settings

# ── Engine ─────────────────────────────────────────────────────────────────
# Created eagerly at module load time so the application fails fast if
# DATABASE_URL is invalid.  psycopg2-binary must be installed in the runtime
# environment.
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,      # guards against stale connections after idle period
    echo=settings.debug,     # SQL logging in development; off in production
)

# ── Session Factory ────────────────────────────────────────────────────────
# autocommit=False: transactions are explicit — callers commit or rollback.
# autoflush=False: prevents implicit flushes before queries (safer for tests).
SessionLocal = sessionmaker(
    bind=engine,
    class_=Session,
    autocommit=False,
    autoflush=False,
)


# ── FastAPI Dependency ─────────────────────────────────────────────────────
def get_db() -> Generator[Session, None, None]:
    """
    Yield a database session for one HTTP request lifecycle.

    Usage in FastAPI route handlers:

        from fastapi import Depends
        from sqlalchemy.orm import Session
        from app.db.session import get_db

        @router.get("/example")
        def example(db: Session = Depends(get_db)):
            ...

    The session is always closed in the finally block regardless of whether
    the request succeeds or raises an exception.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
