"""Tests for 4xx client error handling and validation robustness."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_not_found_returns_404(async_client: AsyncClient) -> None:
    """Verify non-existent routes return 404 with request ID."""
    response = await async_client.get("/non-existent-route-xyz")
    assert response.status_code == 404
    assert "X-Request-ID" in response.headers


@pytest.mark.asyncio
async def test_validation_error_returns_422(async_client: AsyncClient) -> None:
    """Verify invalid payloads trigger 422 Unprocessable Entity (not 500)."""
    # Empty message violates min_length=1
    response = await async_client.post("/api/v1/echo", json={"message": ""})
    assert response.status_code == 422
    data = response.json()
    assert data["error"] == "Validation Error"
    assert "detail" in data
    assert "X-Request-ID" in response.headers


@pytest.mark.asyncio
async def test_missing_field_returns_422(async_client: AsyncClient) -> None:
    """Verify missing required fields trigger 422."""
    response = await async_client.post("/api/v1/echo", json={})
    assert response.status_code == 422
    data = response.json()
    assert data["error"] == "Validation Error"


@pytest.mark.asyncio
async def test_valid_echo_returns_200(async_client: AsyncClient) -> None:
    """Verify valid payload succeeds."""
    response = await async_client.post("/api/v1/echo", json={"message": "hello recruit lens"})
    assert response.status_code == 200
    assert response.json() == {"echo": "hello recruit lens"}
