"""Background task polling and status inspection endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas import BackgroundTaskResponse
from app.auth.dependencies import get_current_user
from app.db.models import BackgroundTask, User
from app.db.session import get_db

router = APIRouter(prefix="/tasks", tags=["Tasks"])


@router.get("/{task_id}", response_model=BackgroundTaskResponse)
async def get_task_status(
    task_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> BackgroundTaskResponse:
    """Retrieve progress and completion state for an asynchronous background task."""
    res = await db.execute(
        select(BackgroundTask).where(
            BackgroundTask.id == task_id,
            BackgroundTask.tenant_id == current_user.tenant_id,
        )
    )
    task = res.scalar_one_or_none()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Background task not found"
        )

    return BackgroundTaskResponse.model_validate(task)
