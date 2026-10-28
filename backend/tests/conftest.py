"""Pytest fixtures for backend test suite."""

from collections.abc import AsyncGenerator

import pytest
from app.main import app
from httpx import ASGITransport, AsyncClient


@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Provide an asynchronous HTTP test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
