"""Authentication package exports."""

from app.auth.dependencies import get_current_tenant, get_current_user, require_role
from app.auth.schemas import (
    RefreshTokenRequest,
    TenantCreateRequest,
    TenantResponse,
    TokenResponse,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
)
from app.auth.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)

__all__ = [
    "get_current_user",
    "get_current_tenant",
    "require_role",
    "hash_password",
    "verify_password",
    "create_access_token",
    "create_refresh_token",
    "decode_token",
    "TenantCreateRequest",
    "TenantResponse",
    "UserRegisterRequest",
    "UserLoginRequest",
    "TokenResponse",
    "RefreshTokenRequest",
    "UserResponse",
]
