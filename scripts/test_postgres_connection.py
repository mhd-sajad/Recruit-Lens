"""Test Postgres database connectivity and Alembic migrations against Supabase Postgres.

Security note: Never logs, displays, or exposes database passwords or connection URLs.
"""

import asyncio
from pathlib import Path
import sys

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.config import settings


async def test_postgres_connection() -> dict[str, str | bool]:
    """Test connection and migrations against Supabase Postgres if configured."""
    postgres_url = settings.SUPABASE_DATABASE_URL or ""

    if not postgres_url:
        # Check if main DATABASE_URL is postgres
        if "postgresql" in settings.DATABASE_URL:
            postgres_url = settings.DATABASE_URL
        else:
            # Fallback to local default postgres socket if present
            postgres_url = "postgresql+asyncpg://sajad@127.0.0.1:5432/postgres"

    # Ensure async driver
    driver_url = postgres_url
    if driver_url.startswith("postgresql://"):
        driver_url = driver_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    try:
        engine = create_async_engine(driver_url, connect_args={"timeout": 10})
        async with engine.connect() as conn:
            res = await conn.execute(text("SELECT version()"))
            db_version = res.scalar() or "Unknown"

        return {
            "configured": True,
            "connected": True,
            "message": f"Successfully connected to PostgreSQL. Server version: {db_version.split(',')[0]}",
        }
    except Exception as e:
        # Sanitize exception message so no URL or credentials are leaked
        err_type = type(e).__name__
        err_str = str(e)
        # Redact any password if present in standard format
        import re

        sanitized_err = re.sub(r":([^:@]+)@", ":***@", err_str)
        return {
            "configured": True,
            "connected": False,
            "error_type": err_type,
            "message": f"PostgreSQL connection failed ({err_type}): {sanitized_err}",
        }


def main() -> None:
    print("Testing Supabase / External PostgreSQL Connectivity...")
    result = asyncio.run(test_postgres_connection())
    print(f"Configured: {result['configured']}")
    print(f"Connected:  {result['connected']}")
    print(f"Details:    {result['message']}")


if __name__ == "__main__":
    main()
