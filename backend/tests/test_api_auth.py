"""Integration tests for authentication API endpoints, throttling, and refresh token rotation with reuse detection."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.auth.security import hash_password
from app.db.models import User
from app.db.session import AsyncSessionLocal, init_db
from app.main import app


@pytest.mark.asyncio
async def test_auth_login_refresh_rotation_reuse_detection_and_me() -> None:
    """Verify login, token rotation, theft reuse detection, and profile retrieval."""
    await init_db()

    # Seed test recruiter user directly (no public signup endpoint)
    async with AsyncSessionLocal() as db:
        user = User(
            email="auth_tester@recruitlens.local",
            hashed_password=hash_password("ValidPassword123!"),
            full_name="Auth Tester",
            role="recruiter",
        )
        db.add(user)
        await db.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Login with valid credentials
        res_login = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "auth_tester@recruitlens.local",
                "password": "ValidPassword123!",
            },
        )
        assert res_login.status_code == 200
        data_login = res_login.json()
        assert "access_token" in data_login
        assert "refresh_token" in data_login
        access_tok = data_login["access_token"]
        refresh_tok = data_login["refresh_token"]

        # 2. Get profile with access token
        res_me = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {access_tok}"},
        )
        assert res_me.status_code == 200
        data_me = res_me.json()
        assert data_me["email"] == "auth_tester@recruitlens.local"
        assert data_me["role"] == "recruiter"
        assert data_me["is_active"] is True

        # 3. Refresh token rotation: valid refresh produces NEW token pair
        res_refresh = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_tok},
        )
        assert res_refresh.status_code == 200
        data_refresh = res_refresh.json()
        new_access_tok = data_refresh["access_token"]
        new_refresh_tok = data_refresh["refresh_token"]
        assert new_access_tok != access_tok
        assert new_refresh_tok != refresh_tok

        # 4. Refresh token theft / reuse detection:
        # Replaying the old (now revoked) refresh token must be detected as theft,
        # invalidating the entire family and returning 401
        res_reuse = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_tok},
        )
        assert res_reuse.status_code == 401
        assert "compromised" in str(res_reuse.json()).lower()

        # 5. The new refresh token should also be revoked because the entire family was invalidated
        res_invalidated = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": new_refresh_tok},
        )
        assert res_invalidated.status_code == 401


@pytest.mark.asyncio
async def test_auth_login_throttling() -> None:
    """Verify login throttling kicks in after repeated failed login attempts."""
    await init_db()

    async with AsyncSessionLocal() as db:
        user = User(
            email="throttle_victim@recruitlens.local",
            hashed_password=hash_password("ValidPassword123!"),
            full_name="Throttle Victim",
            role="recruiter",
        )
        db.add(user)
        await db.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 5 consecutive bad logins
        for _ in range(5):
            res_bad = await client.post(
                "/api/v1/auth/login",
                json={
                    "email": "throttle_victim@recruitlens.local",
                    "password": "WrongPassword!",
                },
            )
            assert res_bad.status_code == 401

        # 6th attempt is throttled with 429
        res_throttled = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "throttle_victim@recruitlens.local",
                "password": "ValidPassword123!",
            },
        )
        assert res_throttled.status_code == 429
        assert "too many" in str(res_throttled.json()).lower()
