"""Pydantic schemas for authentication and user management."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


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


class UserCreateRequest(BaseModel):
    """Admin CLI / script user creation payload."""

    email: str = Field(pattern=EMAIL_PATTERN)
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(default="", max_length=100)
    role: str = Field(default="recruiter", pattern=r"^(admin|recruiter|reviewer)$")


class UserResponse(BaseModel):
    """Authenticated user profile representation."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    full_name: str
    role: str
    is_active: bool
    daily_token_usage: int
    created_at: datetime
