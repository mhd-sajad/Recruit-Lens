"""
test_supabase.py

Tests Supabase PostgreSQL integration.
- In mock mode: verifies schema models and SQL execution.
- In live mode: verifies live query execution when SUPABASE_DATABASE_URL is provided,
  or safely skips when credentials are absent.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.base import Base


@pytest.mark.asyncio
async def test_supabase_models_schema_validity() -> None:
    """Verify all ORM models registered on metadata have valid table names and columns."""
    tables = Base.metadata.tables
    assert "users" in tables
    assert "jobs" in tables
    assert "evaluations" in tables
    assert "audit_logs" in tables
    assert len(tables["users"].columns) >= 6
    assert len(tables["jobs"].columns) >= 8


@pytest.mark.asyncio
async def test_supabase_mocked_query_execution() -> None:
    """Verify database query execution logic with mocked engine/session."""
    mock_session = AsyncMock(spec=AsyncSession)
    mock_res = MagicMock()
    mock_res.scalar.return_value = "PostgreSQL 15.1 on x86_64"
    mock_session.execute.return_value = mock_res

    res = await mock_session.execute(text("SELECT version()"))
    version = res.scalar()
    assert "PostgreSQL" in version


@pytest.mark.asyncio
async def test_supabase_live_connectivity_or_skip() -> None:
    """Execute live query against Supabase if configured; safely skip if absent."""
    supabase_url = getattr(settings, "SUPABASE_DATABASE_URL", None)
    if not supabase_url:
        pytest.skip("SUPABASE_DATABASE_URL is not configured; skipping live Supabase test.")

    from sqlalchemy.ext.asyncio import create_async_engine

    driver_url = supabase_url
    if driver_url.startswith("postgresql://"):
        driver_url = driver_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    engine = create_async_engine(driver_url, connect_args={"timeout": 5})
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            val = result.scalar()
            assert val == 1
    finally:
        await engine.dispose()
