from __future__ import annotations

import os
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import event, text

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.environ.get("DB_PATH", os.path.join(BASE_DIR, "..", "watchlist.db"))
DATABASE_URL = f"sqlite+aiosqlite:///{os.path.abspath(DB_PATH)}"


# ---------------------------------------------------------------------------
# Engine – WAL mode is set via a connect event so it applies at connection
# creation time, before any ORM operation touches the file.
# ---------------------------------------------------------------------------
engine: AsyncEngine = create_async_engine(
    DATABASE_URL,
    echo=False,              # Set to True for SQL query logging during debug
    pool_pre_ping=True,
    connect_args={
        "check_same_thread": False,   # Required for SQLite with async
    },
)


@event.listens_for(engine.sync_engine, "connect")
def _set_sqlite_pragma(dbapi_connection, _connection_record):
    """Enable WAL mode and recommended SQLite pragmas on every new connection."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL;")
    cursor.execute("PRAGMA synchronous=NORMAL;")   # Balance durability vs speed
    cursor.execute("PRAGMA foreign_keys=ON;")
    cursor.execute("PRAGMA temp_store=MEMORY;")
    cursor.execute("PRAGMA mmap_size=134217728;")  # 128 MB memory-mapped I/O
    cursor.close()


# ---------------------------------------------------------------------------
# Session factory
# ---------------------------------------------------------------------------
AsyncSessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,   # Prevent lazy-load errors after commit
    autoflush=False,
    autocommit=False,
)


# ---------------------------------------------------------------------------
# ORM Base
# ---------------------------------------------------------------------------
class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""
    pass


# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Yields an async DB session for use as a FastAPI dependency.
    The session is always closed in the finally block, even on errors.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ---------------------------------------------------------------------------
# Table initialization helper (called from main.py lifespan)
# ---------------------------------------------------------------------------
async def init_db() -> None:
    """Create all tables if they don't exist. Idempotent."""
    async with engine.begin() as conn:
        from app.models import Base as ModelBase  # noqa: avoid circular import
        await conn.run_sync(ModelBase.metadata.create_all)
