"""Authentication endpoints: registration, login, token refresh, and user profile."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.auth.schemas import (
    RefreshTokenRequest,
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
from app.config import settings
from app.db.models import Tenant, User
from app.db.session import get_db

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    req: UserRegisterRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenResponse:
    """Register a new organization tenant and primary admin account."""
    # Check if slug exists
    slug_res = await db.execute(select(Tenant).where(Tenant.slug == req.tenant_slug))
    tenant = slug_res.scalar_one_or_none()
    if tenant is None:
        tenant = Tenant(name=req.tenant_name, slug=req.tenant_slug)
        db.add(tenant)
        await db.flush()

    # Check if email exists in this tenant
    user_res = await db.execute(
        select(User).where(User.tenant_id == tenant.id, User.email == req.email.lower())
    )
    if user_res.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email already exists in this organization",
        )

    # Hash password with Argon2
    hashed = hash_password(req.password)
    user = User(
        tenant_id=tenant.id,
        email=req.email.lower(),
        hashed_password=hashed,
        full_name=req.full_name or req.email.split("@")[0],
        role="admin",
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    token_claims = {"sub": user.id, "tenant_id": tenant.id, "role": user.role}
    access_tok = create_access_token(token_claims)
    refresh_tok = create_refresh_token(token_claims)

    return TokenResponse(
        access_token=access_tok,
        refresh_token=refresh_tok,
        expires_in_seconds=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/login", response_model=TokenResponse)
async def login_user(
    req: UserLoginRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenResponse:
    """Authenticate with email and password and receive JWT tokens."""
    res = await db.execute(select(User).where(User.email == req.email.lower()))
    user = res.scalar_one_or_none()
    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account has been deactivated",
        )

    token_claims = {"sub": user.id, "tenant_id": user.tenant_id, "role": user.role}
    access_tok = create_access_token(token_claims)
    refresh_tok = create_refresh_token(token_claims)

    return TokenResponse(
        access_token=access_tok,
        refresh_token=refresh_tok,
        expires_in_seconds=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_access_token(
    req: RefreshTokenRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenResponse:
    """Rotate expired access token using valid refresh token."""
    payload = decode_token(req.refresh_token)
    if payload is None or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    user_id = payload.get("sub")
    tenant_id = payload.get("tenant_id")
    res = await db.execute(select(User).where(User.id == user_id, User.tenant_id == tenant_id))
    user = res.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account no longer active",
        )

    token_claims = {"sub": user.id, "tenant_id": user.tenant_id, "role": user.role}
    new_access = create_access_token(token_claims)
    new_refresh = create_refresh_token(token_claims)

    return TokenResponse(
        access_token=new_access,
        refresh_token=new_refresh,
        expires_in_seconds=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.get("/me", response_model=UserResponse)
async def get_my_profile(
    current_user: Annotated[User, Depends(get_current_user)],
) -> UserResponse:
    """Return profile of currently authenticated user."""
    return UserResponse.model_validate(current_user)
