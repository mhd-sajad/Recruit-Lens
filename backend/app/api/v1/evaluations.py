"""Candidate evaluation, scoring rankings, recruiter decision workflow, and on-demand LLM generation."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.v1.schemas import (
    CandidateDecisionRequest,
    CandidateDecisionResponse,
    EvaluationDetailResponse,
    EvaluationSummaryResponse,
)
from app.auth.dependencies import get_current_user
from app.db.models import AuditLog, Evaluation, User
from app.db.session import get_db
from app.worker.tasks import generate_on_demand_llm_text

router = APIRouter(prefix="/evaluations", tags=["Evaluations"])


@router.get("/job/{job_id}", response_model=list[EvaluationSummaryResponse])
async def list_evaluations_for_job(
    job_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    tier: str | None = Query(None, description="Filter by candidate fit tier"),
    decision: str | None = Query(None, description="Filter by recruiter decision state"),
) -> list[EvaluationSummaryResponse]:
    """Retrieve ranked candidate evaluation list for a specific job requisition."""
    query = (
        select(Evaluation)
        .options(selectinload(Evaluation.resume))
        .where(
            Evaluation.job_id == job_id,
            Evaluation.tenant_id == current_user.tenant_id,
        )
    )

    if tier:
        query = query.where(Evaluation.tier == tier)
    if decision:
        query = query.where(Evaluation.decision == decision)

    query = query.order_by(Evaluation.total_score.desc())
    res = await db.execute(query)
    evaluations = res.scalars().all()

    summary_list: list[EvaluationSummaryResponse] = []
    for ev in evaluations:
        filename = ev.resume.filename if ev.resume else "unknown.pdf"
        summary_list.append(
            EvaluationSummaryResponse(
                id=ev.id,
                resume_id=ev.resume_id,
                job_id=ev.job_id,
                candidate_filename=filename,
                total_score=ev.total_score,
                tier=ev.tier,
                confidence=ev.confidence,
                decision=ev.decision,
                llm_generated=ev.llm_generated,
                created_at=ev.created_at,
            )
        )
    return summary_list


@router.get("/{id}", response_model=EvaluationDetailResponse)
async def get_evaluation_detail(
    id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> EvaluationDetailResponse:
    """Retrieve detailed candidate evaluation dossier with citations and generated texts."""
    res = await db.execute(
        select(Evaluation)
        .options(selectinload(Evaluation.resume))
        .where(Evaluation.id == id, Evaluation.tenant_id == current_user.tenant_id)
    )
    ev = res.scalar_one_or_none()
    if not ev:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evaluation not found")

    filename = ev.resume.filename if ev.resume else "unknown.pdf"

    return EvaluationDetailResponse(
        id=ev.id,
        tenant_id=ev.tenant_id,
        job_id=ev.job_id,
        resume_id=ev.resume_id,
        candidate_filename=filename,
        total_score=ev.total_score,
        tier=ev.tier,
        confidence=ev.confidence,
        decision=ev.decision,
        decision_notes=ev.decision_notes,
        breakdown=ev.breakdown_json,
        explanation=ev.explanation_json,
        interview_questions=ev.questions_json,
        email_drafts=ev.email_drafts_json,
        evidence_hash=ev.evidence_hash,
        llm_generated=ev.llm_generated,
        created_at=ev.created_at,
        updated_at=ev.updated_at,
    )


@router.post("/{id}/decision", response_model=CandidateDecisionResponse)
async def record_candidate_decision(
    id: str,
    req: CandidateDecisionRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CandidateDecisionResponse:
    """Record human recruiter decision action and append immutable audit log."""
    res = await db.execute(
        select(Evaluation).where(
            Evaluation.id == id, Evaluation.tenant_id == current_user.tenant_id
        )
    )
    ev = res.scalar_one_or_none()
    if not ev:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evaluation not found")

    prev_decision = ev.decision
    ev.decision = req.decision
    ev.decision_notes = req.decision_notes

    # Create immutable audit log entry
    audit_log = AuditLog(
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        action="candidate_decision",
        target_type="evaluation",
        target_id=ev.id,
        details_json={
            "previous_decision": prev_decision,
            "new_decision": req.decision,
            "decision_notes": req.decision_notes,
            "candidate_tier": ev.tier,
            "candidate_score": ev.total_score,
            "decided_by_email": current_user.email,
        },
    )
    db.add(audit_log)
    await db.commit()
    await db.refresh(ev)
    await db.refresh(audit_log)

    return CandidateDecisionResponse(
        id=ev.id,
        evaluation_id=ev.id,
        decision=ev.decision,
        decision_notes=ev.decision_notes,
        audit_log_id=audit_log.id,
        updated_at=ev.updated_at,
    )


@router.post("/{id}/generate-text", response_model=EvaluationDetailResponse)
async def generate_evaluation_text_on_demand(
    id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> EvaluationDetailResponse:
    """Trigger or refresh on-demand LLM text generation with evidence caching."""
    res = await db.execute(
        select(Evaluation).where(
            Evaluation.id == id, Evaluation.tenant_id == current_user.tenant_id
        )
    )
    ev = res.scalar_one_or_none()
    if not ev:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evaluation not found")

    # Run on-demand generation
    success = await generate_on_demand_llm_text(evaluation_id=id, tenant_id=current_user.tenant_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate LLM text from candidate evidence",
        )

    # Reload updated evaluation
    return await get_evaluation_detail(id=id, current_user=current_user, db=db)
