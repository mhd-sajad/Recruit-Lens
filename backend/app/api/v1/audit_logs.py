"""Audit trail inquiry endpoints for enterprise compliance and decision history."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas import AuditLogResponse
from app.auth.dependencies import get_current_user
from app.db.models import AuditLog, User
from app.db.session import get_db

router = APIRouter(prefix="/audit-logs", tags=["Audit Logs"])


@router.get("/", response_model=list[AuditLogResponse])
async def list_audit_logs(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    target_id: str | None = Query(None, description="Filter by target object ID"),
    target_type: str | None = Query(None, description="Filter by target type"),
    action: str | None = Query(None, description="Filter by action name"),
) -> list[AuditLogResponse]:
    """Retrieve immutable audit events for current tenant."""
    query = (
        select(AuditLog)
        .where(AuditLog.tenant_id == current_user.tenant_id)
        .order_by(AuditLog.created_at.desc())
    )

    if target_id:
        query = query.where(AuditLog.target_id == target_id)
    if target_type:
        query = query.where(AuditLog.target_type == target_type)
    if action:
        query = query.where(AuditLog.action == action)

    res = await db.execute(query)
    logs = res.scalars().all()
    return [AuditLogResponse.model_validate(log) for log in logs]
