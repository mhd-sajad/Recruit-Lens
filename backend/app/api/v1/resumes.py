"""Resume upload and document management endpoints."""

import hashlib
from typing import Annotated, Any

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas import ResumeResponse
from app.auth.dependencies import get_current_user
from app.config import settings
from app.db.models import BackgroundTask, Job, Resume, User
from app.db.session import get_db
from app.worker.tasks import process_batch_ingestion

router = APIRouter(prefix="/resumes", tags=["Resumes"])


@router.post("/{job_id}/upload")
async def upload_resumes(
    job_id: str,
    background_tasks: BackgroundTasks,
    files: list[UploadFile] = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Upload batch of PDF resumes, save securely to disk, and enqueue background parsing and scoring."""
    # Verify Job belongs to tenant
    job_res = await db.execute(
        select(Job).where(Job.id == job_id, Job.tenant_id == current_user.tenant_id)
    )
    job = job_res.scalar_one_or_none()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Job requisition not found"
        )

    if not files:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No files provided")

    if len(files) > settings.MAX_BATCH_RESUMES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Batch size exceeds maximum limit of {settings.MAX_BATCH_RESUMES} resumes",
        )

    upload_dir = settings.data_dir / "uploads" / current_user.tenant_id / job_id
    upload_dir.mkdir(parents=True, exist_ok=True)

    max_size_bytes = settings.MAX_UPLOAD_FILE_SIZE_MB * 1024 * 1024
    created_resumes: list[Resume] = []

    for f in files:
        filename = f.filename or "unknown.pdf"
        if not filename.lower().endswith(".pdf"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File '{filename}' is not a PDF document. Only PDF uploads are accepted.",
            )

        contents = await f.read()
        if len(contents) > max_size_bytes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File '{filename}' exceeds maximum allowed size of {settings.MAX_UPLOAD_FILE_SIZE_MB}MB",
            )

        f_hash = hashlib.sha256(contents).hexdigest()
        dest_path = upload_dir / f"{f_hash[:16]}_{filename}"
        with open(dest_path, "wb") as out_f:
            out_f.write(contents)

        resume = Resume(
            tenant_id=current_user.tenant_id,
            job_id=job.id,
            filename=filename,
            file_hash=f_hash,
            file_path=str(dest_path),
            status="uploaded",
        )
        db.add(resume)
        created_resumes.append(resume)

    # Create background task tracker
    task = BackgroundTask(
        tenant_id=current_user.tenant_id,
        job_id=job.id,
        task_type="batch_ingestion",
        status="pending",
        progress=0,
        total=len(created_resumes),
        payload_json={"resume_count": len(created_resumes)},
        result_json={},
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)

    # Enqueue background worker task
    background_tasks.add_task(process_batch_ingestion, task.id)

    return {
        "task_id": task.id,
        "job_id": job.id,
        "files_uploaded": len(created_resumes),
        "status": "processing_queued",
        "resumes": [ResumeResponse.model_validate(r) for r in created_resumes],
    }


@router.get("/{job_id}", response_model=list[ResumeResponse])
async def list_resumes_for_job(
    job_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[ResumeResponse]:
    """List all candidate resumes uploaded for a specific job requisition."""
    res = await db.execute(
        select(Resume)
        .where(Resume.job_id == job_id, Resume.tenant_id == current_user.tenant_id)
        .order_by(Resume.created_at.desc())
    )
    resumes = res.scalars().all()
    return [ResumeResponse.model_validate(r) for r in resumes]
