"""Background task status, Server-Sent Events (SSE) progress streaming, and cancellation."""

import asyncio
import json
from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas import BackgroundTaskResponse
from app.auth.dependencies import get_current_user
from app.db.models import AuditLog, BackgroundTask, User
from app.db.session import AsyncSessionLocal, get_db

router = APIRouter(prefix="/tasks", tags=["Background Tasks"])


@router.get("/{task_id}", response_model=BackgroundTaskResponse)
async def get_task_status(
    task_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> BackgroundTaskResponse:
    """Retrieve current background task status and progress counter. Cross-user returns 404."""
    result = await db.execute(
        select(BackgroundTask).where(
            BackgroundTask.id == task_id, BackgroundTask.user_id == current_user.id
        )
    )
    task = result.scalar_one_or_none()
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Background task '{task_id}' not found",
        )
    return BackgroundTaskResponse.model_validate(task)


@router.get("/{task_id}/events")
async def stream_task_events(
    task_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
) -> StreamingResponse:
    """Stream real-time task progress events via Server-Sent Events (SSE)."""

    async def event_generator() -> AsyncGenerator[str, None]:
        last_progress = -1
        while True:
            async with AsyncSessionLocal() as db:
                res = await db.execute(
                    select(BackgroundTask).where(
                        BackgroundTask.id == task_id, BackgroundTask.user_id == current_user.id
                    )
                )
                task = res.scalar_one_or_none()
                if task is None:
                    yield f"event: error\ndata: {json.dumps({'error': 'Task not found'})}\n\n"
                    break

                if task.progress != last_progress or task.status in (
                    "completed",
                    "failed",
                    "cancelled",
                ):
                    last_progress = task.progress
                    payload = {
                        "task_id": task.id,
                        "status": task.status,
                        "progress": task.progress,
                        "total": task.total,
                        "error": task.error_message,
                    }
                    yield f"event: progress\ndata: {json.dumps(payload)}\n\n"

                if task.status in ("completed", "failed", "cancelled"):
                    break

            await asyncio.sleep(0.5)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("/{task_id}/cancel", response_model=BackgroundTaskResponse)
async def cancel_task(
    task_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> BackgroundTaskResponse:
    """Cancel a pending or in-progress background task."""
    result = await db.execute(
        select(BackgroundTask).where(
            BackgroundTask.id == task_id, BackgroundTask.user_id == current_user.id
        )
    )
    task = result.scalar_one_or_none()
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Background task '{task_id}' not found",
        )

    if task.status in ("completed", "failed"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel task in '{task.status}' state",
        )

    task.status = "cancelled"
    task.error_message = "Task cancelled by user request"

    audit = AuditLog(
        user_id=current_user.id,
        action="cancel_task",
        target_type="task",
        target_id=task.id,
        details_json={"task_type": task.task_type},
    )
    db.add(audit)
    await db.commit()
    await db.refresh(task)

    return BackgroundTaskResponse.model_validate(task)
