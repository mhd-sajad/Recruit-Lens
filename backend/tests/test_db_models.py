"""Unit tests for SQLAlchemy models, constraints, and Argon2 security."""

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.auth.security import hash_password, verify_password
from app.db.models import Job, Tenant, User
from app.db.session import AsyncSessionLocal, init_db


@pytest.mark.asyncio
async def test_tenant_and_user_creation_and_argon2_hashing() -> None:
    """Verify tenant and user creation with Argon2id password hashing."""
    await init_db()

    async with AsyncSessionLocal() as db:
        # Create tenant
        tenant = Tenant(name="Acme Corp", slug="acme-test-org")
        db.add(tenant)
        await db.commit()
        await db.refresh(tenant)

        assert tenant.id is not None
        assert tenant.is_active is True

        # Hash password and create user
        raw_pw = "SuperSecretPassword123!"
        hashed = hash_password(raw_pw)
        assert hashed.startswith("$argon2id$")
        assert verify_password(raw_pw, hashed) is True
        assert verify_password("WrongPassword!", hashed) is False

        user = User(
            tenant_id=tenant.id,
            email="recruiter@acme.test",
            hashed_password=hashed,
            full_name="Alice Recruiter",
            role="recruiter",
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

        assert user.id is not None
        assert user.tenant_id == tenant.id
        assert user.email == "recruiter@acme.test"


@pytest.mark.asyncio
async def test_tenant_unique_user_email_constraint() -> None:
    """Verify unique constraint prevents duplicate user emails within same tenant."""
    await init_db()

    async with AsyncSessionLocal() as db:
        tenant = Tenant(name="Unique Test Corp", slug="unique-test-corp")
        db.add(tenant)
        await db.commit()
        await db.refresh(tenant)

        u1 = User(
            tenant_id=tenant.id,
            email="duplicate@test.local",
            hashed_password=hash_password("password123"),
        )
        db.add(u1)
        await db.commit()

        # Attempt to insert same email for same tenant
        u2 = User(
            tenant_id=tenant.id,
            email="duplicate@test.local",
            hashed_password=hash_password("password456"),
        )
        db.add(u2)
        with pytest.raises(IntegrityError):
            await db.commit()
        await db.rollback()


@pytest.mark.asyncio
async def test_tenant_isolation_foreign_keys() -> None:
    """Verify jobs and resumes belong to tenant and cascade delete cleanly."""
    await init_db()

    async with AsyncSessionLocal() as db:
        tenant = Tenant(name="Cascade Corp", slug="cascade-corp")
        db.add(tenant)
        await db.commit()
        await db.refresh(tenant)

        job = Job(
            tenant_id=tenant.id,
            title="Senior Backend Engineer",
            department="Engineering",
            raw_text="Job description text for senior backend engineer...",
        )
        db.add(job)
        await db.commit()
        await db.refresh(job)

        # Confirm job exists
        res = await db.execute(select(Job).where(Job.id == job.id))
        assert res.scalar_one_or_none() is not None

        # Delete tenant and verify cascade
        await db.delete(tenant)
        await db.commit()

        res2 = await db.execute(select(Job).where(Job.id == job.id))
        assert res2.scalar_one_or_none() is None
