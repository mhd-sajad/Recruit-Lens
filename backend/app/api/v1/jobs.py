"""Job requisition CRUD endpoints with automatic requirements extraction."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas import (
    JobCreateRequest,
    JobExtractRequirementsRequest,
    JobExtractRequirementsResponse,
    JobResponse,
    JobUpdateRequest,
)
from app.auth.dependencies import get_current_user, get_optional_current_user, require_role
from app.core.jd_requirements import extract_job_requirements
from app.core.taxonomy import SkillTaxonomy
from app.db.models import AuditLog, Job, User
from app.db.session import get_db

router = APIRouter(prefix="/jobs", tags=["Jobs"])


@router.post("/extract-requirements", response_model=JobExtractRequirementsResponse)
async def extract_requirements_endpoint(
    payload: JobExtractRequirementsRequest,
    current_user: Annotated[User | None, Depends(get_optional_current_user)] = None,
) -> JobExtractRequirementsResponse:
    """Extract structured skills, experience, and education requirements from raw JD text in real time."""
    taxonomy = SkillTaxonomy.get_instance()
    extracted_reqs = extract_job_requirements(payload.raw_text, taxonomy=taxonomy)
    must = extracted_reqs.must_have_skills
    nice = extracted_reqs.nice_to_have_skills

    suggested: dict[str, float] = {}
    if must:
        total_must = len(must)
        base_int = 100 // total_must
        remainder = 100 % total_must
        for idx, skill in enumerate(must):
            suggested[skill] = float(base_int + (1 if idx < remainder else 0))
    else:
        suggested = {"Core Requirements": 100.0}

    return JobExtractRequirementsResponse(
        must_have_skills=must,
        nice_to_have_skills=nice,
        min_years_experience=extracted_reqs.min_years_experience,
        min_education_name=extracted_reqs.min_education_name,
        suggested_weights=suggested,
    )


@router.post(
    "", response_model=JobResponse, status_code=status.HTTP_201_CREATED, include_in_schema=False
)
@router.post("/", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
async def create_job(
    payload: JobCreateRequest,
    current_user: Annotated[User, Depends(require_role(["recruiter", "admin"]))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> JobResponse:
    """Create job requisition, extract structured requirements, and initialize scoring weights."""
    taxonomy = SkillTaxonomy.get_instance()
    extracted_reqs = extract_job_requirements(payload.raw_text, taxonomy=taxonomy)

    default_weights = {
        "skills": 0.40,
        "experience": 0.30,
        "education": 0.15,
        "semantic": 0.15,
    }
    weights = payload.weights or default_weights

    job = Job(
        user_id=current_user.id,
        title=payload.title,
        department=payload.department,
        raw_text=payload.raw_text,
        requirements_json=extracted_reqs.model_dump(),
        weights_json=weights,
        status="active",
    )
    db.add(job)
    await db.flush()

    audit = AuditLog(
        user_id=current_user.id,
        action="create_job",
        target_type="job",
        target_id=job.id,
        details_json={"title": job.title, "department": job.department},
    )
    db.add(audit)
    await db.commit()
    await db.refresh(job)

    return JobResponse.model_validate(job)


@router.get("", response_model=list[JobResponse], include_in_schema=False)
@router.get("/", response_model=list[JobResponse])
async def list_jobs(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    status_filter: str | None = Query(None, alias="status", description="Filter by job status"),
) -> list[JobResponse]:
    """Retrieve all job requisitions owned by authenticated user."""
    query = select(Job).where(Job.user_id == current_user.id)
    if status_filter:
        query = query.where(Job.status == status_filter)
    query = query.order_by(Job.created_at.desc())

    result = await db.execute(query)
    jobs = result.scalars().all()
    return [JobResponse.model_validate(j) for j in jobs]


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> JobResponse:
    """Fetch single job requisition details. Cross-user access returns 404."""
    result = await db.execute(select(Job).where(Job.id == job_id, Job.user_id == current_user.id))
    job = result.scalar_one_or_none()
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job requisition '{job_id}' not found",
        )
    return JobResponse.model_validate(job)


@router.put("/{job_id}", response_model=JobResponse)
async def update_job(
    job_id: str,
    payload: JobUpdateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> JobResponse:
    """Update job requisition title, text, weights, or status. Cross-user access returns 404."""
    result = await db.execute(select(Job).where(Job.id == job_id, Job.user_id == current_user.id))
    job = result.scalar_one_or_none()
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job requisition '{job_id}' not found",
        )

    if payload.title is not None:
        job.title = payload.title
    if payload.department is not None:
        job.department = payload.department
    if payload.raw_text is not None:
        job.raw_text = payload.raw_text
        taxonomy = SkillTaxonomy.get_instance()
        extracted = extract_job_requirements(job.raw_text, taxonomy=taxonomy)
        job.requirements_json = extracted.model_dump()
    if payload.weights is not None:
        job.weights_json = payload.weights
    if payload.status is not None:
        job.status = payload.status

    audit = AuditLog(
        user_id=current_user.id,
        action="update_job",
        target_type="job",
        target_id=job.id,
        details_json={"updated_fields": list(payload.model_dump(exclude_unset=True).keys())},
    )
    db.add(audit)
    await db.commit()
    await db.refresh(job)

    return JobResponse.model_validate(job)


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_job(
    job_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Delete job requisition. Cross-user access returns 404."""
    result = await db.execute(select(Job).where(Job.id == job_id, Job.user_id == current_user.id))
    job = result.scalar_one_or_none()
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job requisition '{job_id}' not found",
        )

    audit = AuditLog(
        user_id=current_user.id,
        action="delete_job",
        target_type="job",
        target_id=job.id,
        details_json={"deleted_title": job.title},
    )
    db.add(audit)
    await db.delete(job)
    await db.commit()
