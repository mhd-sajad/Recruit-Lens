"""Unit tests for SQLAlchemy models, constraints, per-user isolation, and Argon2 security."""

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.auth.security import hash_password, verify_password
from app.db.models import (
    Job,
    User,
)
from app.db.session import AsyncSessionLocal, init_db


@pytest.mark.asyncio
async def test_user_creation_and_argon2_hashing() -> None:
    """Verify user creation with Argon2id password hashing."""
    await init_db()

    async with AsyncSessionLocal() as db:
        raw_pw = "SuperSecretPassword123!"
        hashed = hash_password(raw_pw)
        assert hashed.startswith("$argon2id$")
        assert verify_password(raw_pw, hashed) is True
        assert verify_password("WrongPassword!", hashed) is False

        user = User(
            email="recruiter_test@acme.test",
            hashed_password=hashed,
            full_name="Alice Recruiter",
            role="recruiter",
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

        assert user.id is not None
        assert user.email == "recruiter_test@acme.test"
        assert user.is_active is True


@pytest.mark.asyncio
async def test_unique_user_email_constraint() -> None:
    """Verify unique constraint prevents duplicate user emails."""
    await init_db()

    async with AsyncSessionLocal() as db:
        u1 = User(
            email="unique_test@test.local",
            hashed_password=hash_password("password123"),
            full_name="User One",
        )
        db.add(u1)
        await db.commit()

        # Attempt to insert same email
        u2 = User(
            email="unique_test@test.local",
            hashed_password=hash_password("password456"),
            full_name="User Two",
        )
        db.add(u2)
        with pytest.raises(IntegrityError):
            await db.commit()
        await db.rollback()


@pytest.mark.asyncio
async def test_user_isolation_foreign_keys_and_cascade() -> None:
    """Verify jobs and resumes belong to user and cascade delete cleanly."""
    await init_db()

    async with AsyncSessionLocal() as db:
        user = User(
            email="cascade_user@test.local",
            hashed_password=hash_password("password123"),
            full_name="Cascade Tester",
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

        job = Job(
            user_id=user.id,
            title="Senior Backend Engineer",
            department="Engineering",
            raw_text="Job description text for senior backend engineer...",
        )
        db.add(job)
        await db.commit()
        await db.refresh(job)

        # Confirm job exists and belongs to user
        res = await db.execute(select(Job).where(Job.id == job.id))
        fetched_job = res.scalar_one_or_none()
        assert fetched_job is not None
        assert fetched_job.user_id == user.id

        # Delete user and verify cascade
        await db.delete(user)
        await db.commit()

        res2 = await db.execute(select(Job).where(Job.id == job.id))
        assert res2.scalar_one_or_none() is None
