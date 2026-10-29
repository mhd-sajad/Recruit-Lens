"""Pytest fixtures for backend test suite."""

from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient

from app.db.base import Base
from app.db.session import engine
from app.main import app


@pytest.fixture(autouse=True)
async def clean_db() -> AsyncGenerator[None, None]:
    """Ensure database schema is fresh and clean for each test function."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Provide an asynchronous HTTP test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
