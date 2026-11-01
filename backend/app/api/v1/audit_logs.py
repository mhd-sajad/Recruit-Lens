"""Audit log retrieval API for user-scoped compliance events."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas import AuditLogResponse
from app.auth.dependencies import get_current_user
from app.db.models import AuditLog, Evaluation, User
from app.db.session import get_db

router = APIRouter(prefix="/audit-logs", tags=["Audit Logs"])


@router.get("", response_model=list[AuditLogResponse], include_in_schema=False)
@router.get("/", response_model=list[AuditLogResponse])
async def list_audit_logs(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    target_id: str | None = Query(None, description="Filter by target object ID"),
    target_type: str | None = Query(None, description="Filter by target type"),
    action: str | None = Query(None, description="Filter by action name"),
    job_id: str | None = Query(None, description="Filter logs for a specific job"),
) -> list[AuditLogResponse]:
    """Retrieve immutable audit events for current user."""
    query = (
        select(AuditLog)
        .where(AuditLog.user_id == current_user.id)
        .order_by(AuditLog.created_at.desc())
    )

    if job_id:
        eval_ids_subq = select(Evaluation.id).where(
            Evaluation.job_id == job_id, Evaluation.user_id == current_user.id
        )
        query = query.where(
            or_(
                and_(AuditLog.target_type == "job", AuditLog.target_id == job_id),
                and_(AuditLog.target_type == "evaluation", AuditLog.target_id.in_(eval_ids_subq)),
            )
        )
    else:
        if target_id:
            query = query.where(AuditLog.target_id == target_id)
        if target_type:
            query = query.where(AuditLog.target_type == target_type)

    if action:
        query = query.where(AuditLog.action == action)

    result = await db.execute(query)
    logs = result.scalars().all()
    return [AuditLogResponse.model_validate(log) for log in logs]
