"""Security utilities: Argon2 password hashing, JWT token handling, password policy, and login throttling."""

import hashlib
import re
import uuid
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from app.config import settings

# Initialize Argon2id password hasher with secure defaults
_hasher = PasswordHasher(
    time_cost=3,
    memory_cost=65536,  # 64 MB memory
    parallelism=4,
    hash_len=32,
    salt_len=16,
)

# In-memory login throttle tracking: identifier -> list of failed attempt timestamps
_failed_logins: dict[str, list[datetime]] = defaultdict(list)


def validate_password_policy(password: str) -> tuple[bool, str]:
    """Enforce strict password complexity policy."""
    if len(password) < 8:
        return False, "Password must be at least 8 characters long."
    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter."
    if not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter."
    if not re.search(r"\d", password):
        return False, "Password must contain at least one number."
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        return False, "Password must contain at least one special character."
    return True, ""


def check_login_throttle(identifier: str) -> tuple[bool, int]:
    """Check if identifier is throttled due to excessive failed attempts.

    Returns (is_allowed, seconds_remaining).
    """
    now = datetime.now(UTC)
    cutoff = now - timedelta(minutes=settings.LOGIN_LOCKOUT_MINUTES)
    recent = [t for t in _failed_logins.get(identifier, []) if t > cutoff]
    _failed_logins[identifier] = recent

    if len(recent) >= settings.LOGIN_MAX_FAILED_ATTEMPTS:
        oldest_in_window = recent[0]
        remaining = int(
            (
                oldest_in_window + timedelta(minutes=settings.LOGIN_LOCKOUT_MINUTES) - now
            ).total_seconds()
        )
        return False, max(remaining, 1)
    return True, 0


def record_failed_login(identifier: str) -> None:
    """Record a failed login attempt for throttling."""
    _failed_logins[identifier].append(datetime.now(UTC))


def reset_failed_logins(identifier: str) -> None:
    """Clear failed login history on successful authentication."""
    _failed_logins.pop(identifier, None)


def hash_password(password: str) -> str:
    """Hash plaintext password using Argon2id."""
    return _hasher.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against Argon2id hash."""
    try:
        return _hasher.verify(hashed_password, plain_password)
    except (VerifyMismatchError, Exception):
        return False


def hash_token(token: str) -> str:
    """Compute SHA-256 hash of token for secure database storage."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    """Create signed HMAC-SHA256 JWT access token."""
    to_encode = data.copy()
    now = datetime.now(UTC)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "iat": now, "type": "access", "jti": str(uuid.uuid4())})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(
    user_id: str,
    token_family: str | None = None,
    expires_delta: timedelta | None = None,
) -> tuple[str, str, str, datetime]:
    """Create signed refresh token returning (raw_jwt, token_hash, token_family, expires_at)."""
    now = datetime.now(UTC)
    family = token_family or str(uuid.uuid4())
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    payload = {
        "sub": user_id,
        "token_family": family,
        "exp": expire,
        "iat": now,
        "type": "refresh",
        "jti": str(uuid.uuid4()),
    }
    raw_token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    token_hash = hash_token(raw_token)
    return raw_token, token_hash, family, expire


def decode_token(token: str) -> dict[str, Any] | None:
    """Decode and validate signature and expiration of JWT token."""
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        return payload
    except Exception:
        return None
