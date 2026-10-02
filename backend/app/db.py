"""Database engines and session factories.

The service uses two SQLAlchemy engines backed by the same psycopg3 driver:

* an **async** engine/session for the I/O-bound request path (movies, health, ratings),
  so request handlers never block the event loop on database round-trips;
* a **sync** engine/session for CPU-bound recommendation work (pgvector queries feeding the
  ALS/hybrid blenders) which is offloaded to a worker thread, plus the background retrainer
  and the offline ``scripts.*`` entrypoints.
"""

from collections.abc import AsyncGenerator, Generator

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings

settings = get_settings()


def _normalize_url(url: str) -> str:
    """Pin the psycopg3 driver.

    Managed-Postgres providers (Render, Railway, Fly, …) hand out URLs with the bare
    ``postgresql://`` scheme, which SQLAlchemy maps to psycopg2. We always use psycopg3
    (``postgresql+psycopg://``), which speaks both sync and async over the same URL.
    """
    for prefix in ("postgresql://", "postgres://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix) :]
    return url


DATABASE_URL = _normalize_url(settings.database_url)

# Sync engine — used by recsys (offloaded to a threadpool), the retrainer, and scripts.
engine = create_engine(DATABASE_URL, pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

# Async engine — used by the request path.
async_engine = create_async_engine(DATABASE_URL, pool_pre_ping=True, future=True)
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine, autoflush=False, expire_on_commit=False, class_=AsyncSession
)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    """Sync session dependency (used by scripts/tests and sync helpers)."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """Async session dependency for request handlers."""
    async with AsyncSessionLocal() as db:
        yield db
