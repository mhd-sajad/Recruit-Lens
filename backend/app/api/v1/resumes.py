"""Resume upload, signed URL generation, and download endpoints."""

import hashlib
import hmac
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas import ResumeResponse
from app.auth.dependencies import get_current_user
from app.config import settings
from app.core.storage import get_storage_backend
from app.db.models import AuditLog, BackgroundTask, Job, Resume, User
from app.db.session import get_db
from app.worker.tasks import process_batch_ingestion

router = APIRouter(prefix="/resumes", tags=["Resumes"])


@router.post("/upload/{job_id}", status_code=status.HTTP_202_ACCEPTED)
async def upload_resumes(
    job_id: str,
    background_tasks: BackgroundTasks,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    files: list[UploadFile] = File(...),
) -> dict[str, Any]:
    """Upload batch of PDF resumes, save securely to storage abstraction, and enqueue background parsing/scoring."""
    # 1. Verify Job exists and belongs to current user (cross-user returns 404)
    job_res = await db.execute(select(Job).where(Job.id == job_id, Job.user_id == current_user.id))
    job = job_res.scalar_one_or_none()
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job requisition '{job_id}' not found",
        )

    if len(files) > settings.MAX_BATCH_RESUMES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Batch size exceeds maximum limit of {settings.MAX_BATCH_RESUMES} resumes",
        )

    storage = get_storage_backend()
    resumes_created: list[Resume] = []
    max_bytes = settings.MAX_UPLOAD_FILE_SIZE_MB * 1024 * 1024

    for upload_file in files:
        if not upload_file.filename or not upload_file.filename.lower().endswith(".pdf"):
            continue

        content = await upload_file.read()
        if len(content) > max_bytes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File '{upload_file.filename}' exceeds maximum {settings.MAX_UPLOAD_FILE_SIZE_MB}MB size",
            )

        file_hash = hashlib.sha256(content).hexdigest()
        file_key = f"{job_id}/{file_hash[:16]}_{upload_file.filename}"

        # Save to storage abstraction
        saved_key = await storage.save_file(file_key, content, content_type="application/pdf")

        resume = Resume(
            user_id=current_user.id,
            job_id=job.id,
            filename=upload_file.filename,
            storage_path=saved_key,
            storage_backend=settings.STORAGE_BACKEND,
            file_hash=file_hash,
            status="pending",
        )
        db.add(resume)
        resumes_created.append(resume)

    if not resumes_created:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No valid PDF documents provided in upload batch",
        )

    # Create background task tracker
    task = BackgroundTask(
        user_id=current_user.id,
        task_type="batch_ingestion",
        status="pending",
        progress=0,
        total=len(resumes_created),
        payload_json={"job_id": job.id, "resume_count": len(resumes_created)},
        result_json={},
    )
    db.add(task)
    await db.flush()

    audit = AuditLog(
        user_id=current_user.id,
        action="upload_resumes_batch",
        target_type="job",
        target_id=job.id,
        details_json={"task_id": task.id, "resume_count": len(resumes_created)},
    )
    db.add(audit)
    await db.commit()

    # Dispatch asynchronous background worker
    background_tasks.add_task(process_batch_ingestion, task.id)

    return {
        "message": f"Successfully queued {len(resumes_created)} resumes for ingestion and scoring",
        "task_id": task.id,
        "job_id": job.id,
        "resume_count": len(resumes_created),
    }


@router.get("/job/{job_id}", response_model=list[ResumeResponse])
async def list_resumes_for_job(
    job_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[ResumeResponse]:
    """Retrieve all uploaded resumes for a job requisition with signed download URLs."""
    # Cross-user returns 404
    job_res = await db.execute(select(Job).where(Job.id == job_id, Job.user_id == current_user.id))
    if job_res.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job requisition '{job_id}' not found",
        )

    res_query = (
        select(Resume)
        .where(Resume.job_id == job_id, Resume.user_id == current_user.id)
        .order_by(Resume.created_at.desc())
    )
    result = await db.execute(res_query)
    resumes = result.scalars().all()

    storage = get_storage_backend()
    responses: list[ResumeResponse] = []
    for r in resumes:
        signed_url = None
        try:
            signed_url = await storage.get_signed_url(r.storage_path, expires_in_seconds=3600)
        except Exception:
            pass

        responses.append(
            ResumeResponse(
                id=r.id,
                job_id=r.job_id,
                filename=r.filename,
                file_hash=r.file_hash,
                status=r.status,
                storage_backend=r.storage_backend,
                signed_url=signed_url,
                created_at=r.created_at,
            )
        )
    return responses


@router.get("/download/{file_path:path}")
async def download_resume_file(
    file_path: str,
    exp: int = Query(..., description="Signature expiration unix epoch"),
    sig: str = Query(..., description="HMAC-SHA256 signature"),
) -> Response:
    """Download resume using signed URL with HMAC verification."""
    # Check expiration
    now = int(datetime.now(UTC).timestamp())
    if now > exp:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Signed download URL expired"
        )

    # Verify HMAC
    signing_secret = settings.JWT_SECRET_KEY.encode("utf-8")
    expected_sig = hmac.new(
        signing_secret, f"{file_path}:{exp}".encode(), hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(sig, expected_sig):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Invalid signature for signed URL"
        )

    storage = get_storage_backend()
    try:
        content = await storage.get_file(file_path)
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="File not found in storage"
        ) from None

    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{file_path.split("/")[-1]}"'},
    )
