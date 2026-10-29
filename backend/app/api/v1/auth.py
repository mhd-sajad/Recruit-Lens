"""Authentication API endpoints: login, token refresh with rotation, and user profile."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas import UserSettingsResponse, UserSettingsUpdate
from app.auth.dependencies import get_current_user
from app.auth.schemas import (
    RefreshTokenRequest,
    TokenResponse,
    UserLoginRequest,
    UserResponse,
)
from app.auth.security import (
    check_login_throttle,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_token,
    record_failed_login,
    reset_failed_logins,
    verify_password,
)
from app.config import settings
from app.db.models import AuditLog, RefreshTokenRecord, User
from app.db.session import get_db

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: UserLoginRequest,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenResponse:
    """Authenticate recruiter via email and password, issuing access and refresh tokens.

    Protected by IP/account login throttling.
    """
    client_ip = request.client.host if request.client else "unknown"
    throttle_key = f"{client_ip}:{payload.email.lower()}"

    allowed, seconds_left = check_login_throttle(throttle_key)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many failed login attempts. Locked out for {seconds_left} seconds.",
        )

    result = await db.execute(select(User).where(User.email == payload.email.lower()))
    user = result.scalar_one_or_none()

    if user is None or not verify_password(payload.password, user.hashed_password):
        record_failed_login(throttle_key)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated. Contact your administrator.",
        )

    reset_failed_logins(throttle_key)

    # 1. Issue access token
    access_token = create_access_token(
        data={"sub": user.id, "email": user.email, "role": user.role}
    )

    # 2. Issue refresh token and persist in token family for rotation
    refresh_jwt, token_hash, family, expires_at = create_refresh_token(user.id)
    token_rec = RefreshTokenRecord(
        user_id=user.id,
        token_hash=token_hash,
        token_family=family,
        is_revoked=False,
        expires_at=expires_at,
    )
    db.add(token_rec)

    # Audit log
    audit = AuditLog(
        user_id=user.id,
        action="user_login",
        target_type="user",
        target_id=user.id,
        details_json={"ip": client_ip, "role": user.role},
        ip_address=client_ip,
    )
    db.add(audit)
    await db.commit()

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_jwt,
        expires_in_seconds=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_access_token(
    payload: RefreshTokenRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenResponse:
    """Rotate refresh token and issue new access token.

    Detects token reuse (theft detection) by invalidating the entire token family if a revoked
    token is submitted.
    """
    decoded = decode_token(payload.refresh_token)
    if decoded is None or decoded.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    user_id = decoded.get("sub")
    token_family = decoded.get("token_family")
    provided_hash = hash_token(payload.refresh_token)

    # Look up token record
    res = await db.execute(
        select(RefreshTokenRecord).where(RefreshTokenRecord.token_hash == provided_hash)
    )
    token_rec = res.scalar_one_or_none()

    if token_rec is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token not recognized or already purged",
        )

    # TOKEN REUSE DETECTION: If token is already revoked, compromise detected!
    if token_rec.is_revoked:
        # Invalidate ALL tokens in this family immediately!
        await db.execute(
            update(RefreshTokenRecord)
            .where(RefreshTokenRecord.token_family == token_family)
            .values(is_revoked=True)
        )
        audit = AuditLog(
            user_id=user_id,
            action="token_reuse_detected",
            target_type="refresh_token",
            target_id=token_rec.id,
            details_json={"token_family": token_family, "warning": "Family revoked due to reuse"},
        )
        db.add(audit)
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Compromised refresh token detected: session terminated",
        )

    # Revoke used token
    token_rec.is_revoked = True

    # Resolve user
    user_res = await db.execute(select(User).where(User.id == user_id))
    user = user_res.scalar_one_or_none()
    if user is None or not user.is_active:
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User no longer active",
        )

    # Issue new token pair preserving the token family
    new_access_token = create_access_token(
        data={"sub": user.id, "email": user.email, "role": user.role}
    )
    new_refresh_jwt, new_hash, family, expires_at = create_refresh_token(
        user.id, token_family=token_family
    )
    new_rec = RefreshTokenRecord(
        user_id=user.id,
        token_hash=new_hash,
        token_family=family,
        is_revoked=False,
        expires_at=expires_at,
    )
    db.add(new_rec)
    await db.commit()

    return TokenResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_jwt,
        expires_in_seconds=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: Annotated[User, Depends(get_current_user)],
) -> UserResponse:
    """Retrieve profile and token quota of currently authenticated recruiter."""
    return UserResponse.model_validate(current_user)


_USER_SETTINGS: dict[str, dict[str, Any]] = {}


@router.get("/settings", response_model=UserSettingsResponse)
async def get_user_settings(
    current_user: Annotated[User, Depends(get_current_user)],
) -> UserSettingsResponse:
    """Retrieve recruiter UI preferences, blind mode setting, and export options."""
    stored = _USER_SETTINGS.get(current_user.id, {})
    return UserSettingsResponse(
        user_id=current_user.id,
        email=current_user.email,
        role=current_user.role,
        blind_mode_enabled=stored.get("blind_mode_enabled", False),
        dark_mode=stored.get("dark_mode", False),
        export_anonymized=stored.get("export_anonymized", False),
    )


@router.put("/settings", response_model=UserSettingsResponse)
async def update_user_settings(
    payload: UserSettingsUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
) -> UserSettingsResponse:
    """Update recruiter UI preferences, blind mode setting, and export options."""
    stored = _USER_SETTINGS.setdefault(
        current_user.id,
        {"blind_mode_enabled": False, "dark_mode": False, "export_anonymized": False},
    )
    if payload.blind_mode_enabled is not None:
        stored["blind_mode_enabled"] = payload.blind_mode_enabled
    if payload.dark_mode is not None:
        stored["dark_mode"] = payload.dark_mode
    if payload.export_anonymized is not None:
        stored["export_anonymized"] = payload.export_anonymized

    return UserSettingsResponse(
        user_id=current_user.id,
        email=current_user.email,
        role=current_user.role,
        blind_mode_enabled=stored["blind_mode_enabled"],
        dark_mode=stored["dark_mode"],
        export_anonymized=stored["export_anonymized"],
    )
