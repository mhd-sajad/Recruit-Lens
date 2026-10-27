"""Tests for health check endpoints and request correlation."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_endpoint(async_client: AsyncClient) -> None:
    """Verify /health returns 200 with status ok and version."""
    response = await async_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data
    assert "environment" in data
    assert "X-Request-ID" in response.headers


@pytest.mark.asyncio
async def test_ping_endpoint(async_client: AsyncClient) -> None:
    """Verify /api/v1/ping returns 200 with pong True."""
    response = await async_client.get("/api/v1/ping")
    assert response.status_code == 200
    assert response.json() == {"pong": True}
    assert "X-Request-ID" in response.headers


@pytest.mark.asyncio
async def test_custom_request_id_preserved(async_client: AsyncClient) -> None:
    """Verify incoming X-Request-ID is preserved in response."""
    custom_id = "test-custom-request-id-12345"
    response = await async_client.get("/health", headers={"X-Request-ID": custom_id})
    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == custom_id
