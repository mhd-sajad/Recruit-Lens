"""Authentication and authorization package."""

from app.auth.dependencies import get_current_user, get_optional_current_user, require_role
from app.auth.schemas import (
    RefreshTokenRequest,
    TokenResponse,
    UserCreateRequest,
    UserLoginRequest,
    UserResponse,
)
from app.auth.security import (
    check_login_throttle,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    hash_token,
    record_failed_login,
    reset_failed_logins,
    validate_password_policy,
    verify_password,
)

__all__ = [
    "get_current_user",
    "get_optional_current_user",
    "require_role",
    "UserLoginRequest",
    "TokenResponse",
    "RefreshTokenRequest",
    "UserCreateRequest",
    "UserResponse",
    "hash_password",
    "verify_password",
    "validate_password_policy",
    "check_login_throttle",
    "record_failed_login",
    "reset_failed_logins",
    "hash_token",
    "create_access_token",
    "create_refresh_token",
    "decode_token",
]
