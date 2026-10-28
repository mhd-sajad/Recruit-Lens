"""CLI command to create recruiter and administrator user accounts.

No public signup is permitted in production. Accounts must be provisioned via this CLI.
"""

import argparse
import asyncio
from pathlib import Path
import sys

# Ensure backend package is importable
backend_dir = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from sqlalchemy import select

from app.auth.security import hash_password, validate_password_policy
from app.db.models import User
from app.db.session import AsyncSessionLocal, init_db


async def create_user(email: str, password: str, full_name: str, role: str) -> None:
    """Validate password and create user in database."""
    valid, err_msg = validate_password_policy(password)
    if not valid:
        print(f"ERROR: Password policy violation: {err_msg}")
        sys.exit(1)

    await init_db()

    async with AsyncSessionLocal() as db:
        res = await db.execute(select(User).where(User.email == email.lower()))
        existing = res.scalar_one_or_none()
        if existing:
            print(f"ERROR: User with email '{email}' already exists.")
            sys.exit(1)

        user = User(
            email=email.lower(),
            hashed_password=hash_password(password),
            full_name=full_name,
            role=role,
            is_active=True,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

        print(f"SUCCESS: Created {role} account for '{user.email}' (ID: {user.id})")


def main() -> None:
    parser = argparse.ArgumentParser(description="Recruit Lens User Creation CLI")
    parser.add_argument("--email", required=True, help="User email address")
    parser.add_argument("--password", required=True, help="User password (must meet policy)")
    parser.add_argument("--name", default="", help="User full name")
    parser.add_argument(
        "--role",
        default="recruiter",
        choices=["admin", "recruiter", "reviewer"],
        help="Account role",
    )

    args = parser.parse_args()
    asyncio.run(create_user(args.email, args.password, args.name, args.role))


if __name__ == "__main__":
    main()
