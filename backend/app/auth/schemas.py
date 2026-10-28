"""Pydantic schemas for authentication and tenant management."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


class TenantCreateRequest(BaseModel):
    """Organization tenant creation payload."""

    name: str = Field(min_length=2, max_length=100)
    slug: str = Field(min_length=2, max_length=50, pattern=r"^[a-z0-9-]+$")


class TenantResponse(BaseModel):
    """Tenant organization summary."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    slug: str
    is_active: bool
    created_at: datetime


class UserRegisterRequest(BaseModel):
    """User account self-registration payload."""

    tenant_name: str = Field(min_length=2, max_length=100, default="Demo Organization")
    tenant_slug: str = Field(
        min_length=2, max_length=50, default="demo-org", pattern=r"^[a-z0-9-]+$"
    )
    email: str = Field(pattern=EMAIL_PATTERN)
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(default="", max_length=100)


class UserLoginRequest(BaseModel):
    """User login request payload."""

    email: str = Field(pattern=EMAIL_PATTERN)
    password: str


class TokenResponse(BaseModel):
    """JWT access and refresh token pair."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in_seconds: int


class RefreshTokenRequest(BaseModel):
    """Refresh token request payload."""

    refresh_token: str


class UserResponse(BaseModel):
    """Authenticated user profile representation."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    email: str
    full_name: str
    role: str
    is_active: bool
    created_at: datetime
