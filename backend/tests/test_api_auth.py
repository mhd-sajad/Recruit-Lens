"""Integration tests for authentication API endpoints."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.db.session import init_db
from app.main import app


@pytest.mark.asyncio
async def test_auth_registration_login_refresh_and_me() -> None:
    """Verify end-to-end user registration, login, refresh, and profile retrieval."""
    await init_db()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Register new tenant & user
        reg_payload = {
            "tenant_name": "Test Company",
            "tenant_slug": "test-company-auth",
            "email": "admin@testcompany.local",
            "password": "SecurePassword123!",
            "full_name": "Test Admin",
        }
        res_reg = await client.post("/api/v1/auth/register", json=reg_payload)
        assert res_reg.status_code == 201
        data_reg = res_reg.json()
        assert "access_token" in data_reg
        assert "refresh_token" in data_reg
        assert data_reg["token_type"] == "bearer"
        access_tok = data_reg["access_token"]
        refresh_tok = data_reg["refresh_token"]

        # 2. Get profile with access token
        res_me = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {access_tok}"},
        )
        assert res_me.status_code == 200
        data_me = res_me.json()
        assert data_me["email"] == "admin@testcompany.local"
        assert data_me["role"] == "admin"
        assert data_me["is_active"] is True

        # 3. Unauthorized access without token
        res_unauth = await client.get("/api/v1/auth/me")
        assert res_unauth.status_code == 401

        # 4. Unauthorized access with malformed token
        res_bad_tok = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid.token.payload"},
        )
        assert res_bad_tok.status_code == 401

        # 5. Login with valid credentials
        res_login = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "admin@testcompany.local",
                "password": "SecurePassword123!",
            },
        )
        assert res_login.status_code == 200
        data_login = res_login.json()
        assert "access_token" in data_login

        # 6. Login with invalid password
        res_bad_pw = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "admin@testcompany.local",
                "password": "WrongPassword123!",
            },
        )
        assert res_bad_pw.status_code == 401

        # 7. Refresh token
        res_refresh = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_tok},
        )
        assert res_refresh.status_code == 200
        data_refresh = res_refresh.json()
        assert "access_token" in data_refresh
        assert data_refresh["access_token"] != access_tok
