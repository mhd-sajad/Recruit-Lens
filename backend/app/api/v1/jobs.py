"""Job requisition management endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas import JobCreateRequest, JobResponse, JobUpdateRequest
from app.auth.dependencies import get_current_user
from app.core.jd_requirements import extract_job_requirements
from app.core.taxonomy import SkillTaxonomy
from app.db.models import Job, User
from app.db.session import get_db

router = APIRouter(prefix="/jobs", tags=["Jobs"])

_taxonomy: SkillTaxonomy | None = None


def get_taxonomy() -> SkillTaxonomy:
    """Lazily load taxonomy."""
    global _taxonomy
    if _taxonomy is None:
        _taxonomy = SkillTaxonomy.get_instance()
    return _taxonomy


@router.post("/", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
async def create_job(
    req: JobCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> JobResponse:
    """Create a new job posting with automatic structured requirement extraction."""
    tax = get_taxonomy()
    reqs = extract_job_requirements(
        jd_text=req.raw_text, job_id="temp", title=req.title, taxonomy=tax
    )

    job = Job(
        tenant_id=current_user.tenant_id,
        title=req.title,
        department=req.department,
        raw_text=req.raw_text,
        requirements_json=reqs.model_dump(),
        weights_json=req.weights or {},
        status="active",
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)
    return JobResponse.model_validate(job)


@router.get("/", response_model=list[JobResponse])
async def list_jobs(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[JobResponse]:
    """List all job requisition postings for current tenant."""
    res = await db.execute(
        select(Job).where(Job.tenant_id == current_user.tenant_id).order_by(Job.created_at.desc())
    )
    jobs = res.scalars().all()
    return [JobResponse.model_validate(j) for j in jobs]


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> JobResponse:
    """Retrieve details for a single job requisition."""
    res = await db.execute(
        select(Job).where(Job.id == job_id, Job.tenant_id == current_user.tenant_id)
    )
    job = res.scalar_one_or_none()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Job requisition not found"
        )
    return JobResponse.model_validate(job)


@router.put("/{job_id}", response_model=JobResponse)
async def update_job(
    job_id: str,
    req: JobUpdateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> JobResponse:
    """Update job title, description, or scoring weights."""
    res = await db.execute(
        select(Job).where(Job.id == job_id, Job.tenant_id == current_user.tenant_id)
    )
    job = res.scalar_one_or_none()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Job requisition not found"
        )

    if req.title is not None:
        job.title = req.title
    if req.department is not None:
        job.department = req.department
    if req.status is not None:
        job.status = req.status
    if req.weights is not None:
        job.weights_json = req.weights

    if req.raw_text is not None and req.raw_text != job.raw_text:
        job.raw_text = req.raw_text
        tax = get_taxonomy()
        reqs = extract_job_requirements(
            jd_text=job.raw_text, job_id=job.id, title=job.title, taxonomy=tax
        )
        job.requirements_json = reqs.model_dump()

    await db.commit()
    await db.refresh(job)
    return JobResponse.model_validate(job)


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_job(
    job_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Delete or archive job requisition."""
    res = await db.execute(
        select(Job).where(Job.id == job_id, Job.tenant_id == current_user.tenant_id)
    )
    job = res.scalar_one_or_none()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Job requisition not found"
        )
    await db.delete(job)
    await db.commit()
