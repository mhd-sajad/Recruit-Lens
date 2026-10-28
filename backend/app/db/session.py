"""Database engine and asynchronous session management."""

from collections.abc import AsyncGenerator
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.db.base import Base


def get_database_url() -> str:
    """Format database URL with proper absolute paths for SQLite if needed."""
    url = settings.DATABASE_URL
    if url.startswith("sqlite+aiosqlite:///"):
        rel_path = url.replace("sqlite+aiosqlite:///", "")
        if not Path(rel_path).is_absolute():
            abs_path = (settings.PROJECT_ROOT / rel_path).resolve()
            abs_path.parent.mkdir(parents=True, exist_ok=True)
            return f"sqlite+aiosqlite:///{abs_path}"
    return url


# Create asynchronous engine
engine = create_async_engine(
    get_database_url(),
    echo=settings.DEBUG,
    future=True,
    # SQLite pool pre-ping
    pool_pre_ping=True,
)

# Create sessionmaker
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency yielding an async database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """Initialize database tables (used for tests and development)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
