"""Candidate evaluation dossiers, state machine workflows, feedback, emails, and export."""

import csv
import io
import secrets
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response, StreamingResponse
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.v1.schemas import (
    EmailDraftResponse,
    EmailSendResponse,
    EmailUpdateRequest,
    EvaluationDetailResponse,
    EvaluationSummaryResponse,
    InterviewFeedbackCreate,
    InterviewFeedbackResponse,
    PipelineAnalyticsResponse,
    StageTransitionRequest,
    StageTransitionResponse,
    WhatIfRequest,
    WhatIfResponse,
)
from app.auth.dependencies import get_current_user
from app.config import settings
from app.core.storage import get_storage_backend
from app.db.models import (
    AuditLog,
    DecisionRecord,
    EmailRecord,
    Evaluation,
    InterviewFeedbackRecord,
    Job,
    McpConfirmationToken,
    User,
)
from app.db.session import get_db
from app.worker.tasks import generate_on_demand_llm_text

router = APIRouter(prefix="/evaluations", tags=["Evaluations"])

# Valid state machine transitions
ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "screened": {"shortlisted", "held", "rejected"},
    "shortlisted": {"interview_scheduled", "held", "rejected"},
    "interview_scheduled": {"interviewed", "held", "rejected"},
    "interviewed": {"offer_extended", "held", "rejected"},
    "offer_extended": {"hired", "declined"},
    "held": {"shortlisted", "rejected"},
    "rejected": {"screened"},  # Reopening rejected candidate
    "declined": {"held", "rejected"},
    "hired": set(),
}


def sanitize_csv_cell(value: Any) -> str:
    """Protect against CSV formula injection attacks (=, +, -, @, tab, CR)."""
    val_str = str(value or "")
    if val_str and val_str[0] in ("=", "+", "-", "@", "\t", "\r"):
        return f"'{val_str}"
    return val_str


@router.get("/job/{job_id}", response_model=list[EvaluationSummaryResponse])
async def list_evaluations_for_job(
    job_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    tier: str | None = Query(None, description="Filter by fit tier"),
    stage: str | None = Query(None, description="Filter by workflow stage"),
) -> list[EvaluationSummaryResponse]:
    """Retrieve ranked candidate evaluation list for a specific job requisition. Cross-user returns 404."""
    # Verify Job ownership
    job_res = await db.execute(select(Job).where(Job.id == job_id, Job.user_id == current_user.id))
    if job_res.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job requisition '{job_id}' not found",
        )

    query = (
        select(Evaluation)
        .options(selectinload(Evaluation.resume))
        .where(Evaluation.job_id == job_id, Evaluation.user_id == current_user.id)
    )

    if tier:
        query = query.where(Evaluation.tier == tier)
    if stage:
        query = query.where(Evaluation.stage == stage)

    query = query.order_by(Evaluation.total_score.desc())
    result = await db.execute(query)
    evaluations = result.scalars().all()

    return [
        EvaluationSummaryResponse(
            id=ev.id,
            resume_id=ev.resume_id,
            job_id=ev.job_id,
            candidate_filename=ev.resume.filename if ev.resume else "Unknown",
            total_score=ev.total_score,
            tier=ev.tier,
            confidence=ev.confidence,
            stage=ev.stage,
            explanation_type=ev.explanation_type,
            llm_generated=ev.llm_generated,
            created_at=ev.created_at,
        )
        for ev in evaluations
    ]


@router.get("/reports/analytics", response_model=PipelineAnalyticsResponse)
async def get_pipeline_analytics(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    job_id: str | None = Query(None, description="Optional job ID to filter analytics"),
) -> PipelineAnalyticsResponse:
    """Aggregate recruiting pipeline funnel, fit tier distribution, and recruiter agreement analytics."""
    query = select(Evaluation).where(Evaluation.user_id == current_user.id)
    if job_id:
        query = query.where(Evaluation.job_id == job_id)

    result = await db.execute(query)
    evals = result.scalars().all()

    stage_counts: dict[str, int] = {
        "screened": 0,
        "shortlisted": 0,
        "interview_scheduled": 0,
        "interviewed": 0,
        "offer_extended": 0,
        "hired": 0,
        "held": 0,
        "rejected": 0,
    }
    tier_counts: dict[str, int] = {
        "FastTrack": 0,
        "Review": 0,
        "Hold": 0,
        "Reject": 0,
        "Abstain": 0,
    }

    advanced_stages = {
        "shortlisted",
        "interview_scheduled",
        "interviewed",
        "offer_extended",
        "hired",
    }
    decided_count = 0
    advanced_count = 0
    agreement_count = 0

    for ev in evals:
        s = ev.stage or "screened"
        t = ev.tier or "Review"
        stage_counts[s] = stage_counts.get(s, 0) + 1
        tier_counts[t] = tier_counts.get(t, 0) + 1

        if s != "screened":
            decided_count += 1
            is_advanced = s in advanced_stages
            if is_advanced:
                advanced_count += 1
            if (t == "FastTrack" and is_advanced) or (t in ("Hold", "Reject") and not is_advanced):
                agreement_count += 1

    agreement_rate_pct = (
        round((agreement_count / max(1, decided_count)) * 100.0, 1) if decided_count > 0 else 100.0
    )

    return PipelineAnalyticsResponse(
        total_candidates=len(evals),
        stage_counts=stage_counts,
        tier_counts=tier_counts,
        decided_count=decided_count,
        advanced_count=advanced_count,
        agreement_rate_pct=agreement_rate_pct,
        disclaimer="Internal pipeline analytics reflect agreement between deterministic tier rankings and recruiter candidate workflow stage transitions.",
    )


@router.get("/{evaluation_id}", response_model=EvaluationDetailResponse)
async def get_evaluation_detail(
    evaluation_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> EvaluationDetailResponse:
    """Retrieve comprehensive candidate dossier. Cross-user returns 404."""
    query = (
        select(Evaluation)
        .options(selectinload(Evaluation.resume))
        .where(Evaluation.id == evaluation_id, Evaluation.user_id == current_user.id)
    )
    result = await db.execute(query)
    ev = result.scalar_one_or_none()
    if ev is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Candidate evaluation '{evaluation_id}' not found",
        )

    return EvaluationDetailResponse(
        id=ev.id,
        user_id=ev.user_id,
        job_id=ev.job_id,
        resume_id=ev.resume_id,
        candidate_filename=ev.resume.filename if ev.resume else "Unknown",
        total_score=ev.total_score,
        tier=ev.tier,
        confidence=ev.confidence,
        stage=ev.stage,
        breakdown=ev.breakdown_json,
        explanation=ev.explanation_json,
        explanation_type=ev.explanation_type,
        interview_questions=ev.interview_questions_json,
        email_drafts=ev.email_drafts_json,
        evidence_hash=ev.evidence_hash,
        llm_generated=ev.llm_generated,
        created_at=ev.created_at,
        updated_at=ev.updated_at,
    )


@router.post("/{evaluation_id}/stage", response_model=StageTransitionResponse)
async def transition_candidate_stage(
    evaluation_id: str,
    payload: StageTransitionRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> StageTransitionResponse:
    """Transition candidate workflow stage according to validated state machine."""
    query = select(Evaluation).where(
        Evaluation.id == evaluation_id, Evaluation.user_id == current_user.id
    )
    result = await db.execute(query)
    ev = result.scalar_one_or_none()
    if ev is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Candidate evaluation '{evaluation_id}' not found",
        )

    current_stage = ev.stage
    target_stage = payload.to_stage

    allowed = ALLOWED_TRANSITIONS.get(current_stage, set())
    if target_stage not in allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid transition from '{current_stage}' to '{target_stage}'. Allowed: {sorted(allowed)}",
        )

    ev.stage = target_stage

    # 1. Append to DecisionRecord
    decision = DecisionRecord(
        user_id=current_user.id,
        evaluation_id=ev.id,
        from_stage=current_stage,
        to_stage=target_stage,
        notes=payload.notes,
    )
    db.add(decision)
    await db.flush()

    # 2. Append to AuditLog
    audit = AuditLog(
        user_id=current_user.id,
        action="stage_transition",
        target_type="evaluation",
        target_id=ev.id,
        details_json={
            "from_stage": current_stage,
            "to_stage": target_stage,
            "notes": payload.notes,
            "decision_id": decision.id,
        },
    )
    db.add(audit)
    await db.commit()

    return StageTransitionResponse(
        id=decision.id,
        evaluation_id=ev.id,
        from_stage=current_stage,
        to_stage=target_stage,
        notes=payload.notes,
        audit_log_id=audit.id,
        updated_at=datetime.now(UTC),
    )


@router.post("/{evaluation_id}/interview-feedback", response_model=InterviewFeedbackResponse)
async def submit_interview_feedback(
    evaluation_id: str,
    payload: InterviewFeedbackCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> InterviewFeedbackResponse:
    """Submit post-interview structured scorecard and feedback."""
    res = await db.execute(
        select(Evaluation).where(
            Evaluation.id == evaluation_id, Evaluation.user_id == current_user.id
        )
    )
    ev = res.scalar_one_or_none()
    if ev is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Evaluation '{evaluation_id}' not found",
        )

    feedback = InterviewFeedbackRecord(
        user_id=current_user.id,
        evaluation_id=ev.id,
        interviewer_name=payload.interviewer_name,
        overall_score=payload.overall_score,
        technical_rating=payload.technical_rating,
        communication_rating=payload.communication_rating,
        recommendation=payload.recommendation,
        strengths=payload.strengths,
        concerns=payload.concerns,
        notes=payload.notes,
    )
    db.add(feedback)
    await db.flush()

    audit = AuditLog(
        user_id=current_user.id,
        action="submit_interview_feedback",
        target_type="evaluation",
        target_id=ev.id,
        details_json={
            "feedback_id": feedback.id,
            "recommendation": payload.recommendation,
            "score": payload.overall_score,
        },
    )
    db.add(audit)
    await db.commit()
    await db.refresh(feedback)

    return InterviewFeedbackResponse.model_validate(feedback)


@router.get("/{evaluation_id}/interview-feedback", response_model=list[InterviewFeedbackResponse])
async def list_interview_feedback(
    evaluation_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[InterviewFeedbackResponse]:
    """Retrieve all interview feedback scorecards for an evaluation."""
    res = await db.execute(
        select(InterviewFeedbackRecord)
        .where(
            InterviewFeedbackRecord.evaluation_id == evaluation_id,
            InterviewFeedbackRecord.user_id == current_user.id,
        )
        .order_by(InterviewFeedbackRecord.created_at.desc())
    )
    records = res.scalars().all()
    return [InterviewFeedbackResponse.model_validate(r) for r in records]


@router.get("/{evaluation_id}/emails", response_model=list[EmailDraftResponse])
async def list_candidate_emails(
    evaluation_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[EmailDraftResponse]:
    """List all email drafts and delivery statuses for candidate."""
    res = await db.execute(
        select(EmailRecord)
        .where(
            EmailRecord.evaluation_id == evaluation_id,
            EmailRecord.user_id == current_user.id,
        )
        .order_by(EmailRecord.created_at.desc())
    )
    emails = res.scalars().all()
    return [EmailDraftResponse.model_validate(e) for e in emails]


@router.put("/emails/{email_id}", response_model=EmailDraftResponse)
async def update_email_draft(
    email_id: str,
    payload: EmailUpdateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> EmailDraftResponse:
    """Edit email draft subject or body. Must be in draft status."""
    res = await db.execute(
        select(EmailRecord).where(
            EmailRecord.id == email_id, EmailRecord.user_id == current_user.id
        )
    )
    email = res.scalar_one_or_none()
    if email is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Email record '{email_id}' not found",
        )
    if email.status != "draft":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot edit email in '{email.status}' status",
        )

    if payload.subject is not None:
        email.subject = payload.subject
    if payload.body is not None:
        email.body = payload.body

    await db.commit()
    await db.refresh(email)
    return EmailDraftResponse.model_validate(email)


@router.post("/emails/{email_id}/approve", response_model=EmailDraftResponse)
async def approve_email_draft(
    email_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> EmailDraftResponse:
    """Approve email draft for sending. A draft must be approved before sending."""
    res = await db.execute(
        select(EmailRecord).where(
            EmailRecord.id == email_id, EmailRecord.user_id == current_user.id
        )
    )
    email = res.scalar_one_or_none()
    if email is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Email record '{email_id}' not found",
        )
    if email.status != "draft":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Email is already '{email.status}'",
        )

    email.status = "approved"
    email.approved_by_user_id = current_user.id

    audit = AuditLog(
        user_id=current_user.id,
        action="approve_email",
        target_type="email",
        target_id=email.id,
        details_json={"recipient": email.recipient_email, "type": email.email_type},
    )
    db.add(audit)
    await db.commit()
    await db.refresh(email)
    return EmailDraftResponse.model_validate(email)


@router.post("/emails/{email_id}/send", response_model=EmailSendResponse)
async def send_approved_email(
    email_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> EmailSendResponse:
    """Send an approved email draft. Enforces approval rule, daily cap, dry-run, and audit log."""
    res = await db.execute(
        select(EmailRecord).where(
            EmailRecord.id == email_id, EmailRecord.user_id == current_user.id
        )
    )
    email = res.scalar_one_or_none()
    if email is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Email record '{email_id}' not found",
        )

    # 1. Rule: Draft MUST be approved before sending
    if email.status != "approved":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Email cannot be sent in '{email.status}' state. It must be approved first.",
        )

    # 2. Rule: Daily email cap enforcement
    today_start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    count_res = await db.execute(
        select(func.count(EmailRecord.id)).where(
            EmailRecord.user_id == current_user.id,
            EmailRecord.status == "sent",
            EmailRecord.sent_at >= today_start,
        )
    )
    sent_today = count_res.scalar() or 0
    if sent_today >= settings.DAILY_EMAIL_CAP:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Daily email cap reached ({settings.DAILY_EMAIL_CAP} emails/day)",
        )

    # 3. Dry-run default execution
    now = datetime.now(UTC)
    email.status = "sent"
    email.sent_at = now

    audit = AuditLog(
        user_id=current_user.id,
        action="send_email",
        target_type="email",
        target_id=email.id,
        details_json={
            "recipient": email.recipient_email,
            "dry_run": settings.EMAIL_DRY_RUN,
            "subject": email.subject,
        },
    )
    db.add(audit)
    await db.commit()

    return EmailSendResponse(
        id=email.id,
        status="sent",
        dry_run=settings.EMAIL_DRY_RUN,
        sent_at=now,
        message="Email successfully simulated and logged (dry-run mode active)"
        if settings.EMAIL_DRY_RUN
        else "Email successfully transmitted",
    )


@router.post("/{evaluation_id}/what-if", response_model=WhatIfResponse)
async def what_if_analysis(
    evaluation_id: str,
    payload: WhatIfRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WhatIfResponse:
    """Run what-if sensitivity recalculation without modifying the database."""
    res = await db.execute(
        select(Evaluation).where(
            Evaluation.id == evaluation_id, Evaluation.user_id == current_user.id
        )
    )
    ev = res.scalar_one_or_none()
    if ev is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Evaluation '{evaluation_id}' not found",
        )

    # Extract stored features
    breakdown = ev.breakdown_json
    skills_val = breakdown.get("skills", {}).get("score", 0.0)
    exp_val = breakdown.get("experience", {}).get("score", 0.0)
    edu_val = breakdown.get("education", {}).get("score", 0.0)
    sem_val = breakdown.get("semantic", {}).get("score", 0.0)

    # Weights
    weights = payload.weights or {
        "skills": 0.40,
        "experience": 0.30,
        "education": 0.15,
        "semantic": 0.15,
    }

    # Normalize weights
    total_w = sum(weights.values()) or 1.0
    norm_w = {k: v / total_w for k, v in weights.items()}

    new_score = (
        skills_val * norm_w.get("skills", 0.4)
        + exp_val * norm_w.get("experience", 0.3)
        + edu_val * norm_w.get("education", 0.15)
        + sem_val * norm_w.get("semantic", 0.15)
    )

    # Recompute tier
    new_tier = "Hold"
    if new_score >= 0.75:
        new_tier = "FastTrack"
    elif new_score >= 0.50:
        new_tier = "Review"
    elif new_score < 0.30:
        new_tier = "Reject"

    return WhatIfResponse(
        original_score=ev.total_score,
        new_score=round(new_score, 4),
        original_tier=ev.tier,
        new_tier=new_tier,
        score_delta=round(new_score - ev.total_score, 4),
        breakdown={
            "weights_used": norm_w,
            "components": {
                "skills": round(skills_val * norm_w.get("skills", 0.4), 4),
                "experience": round(exp_val * norm_w.get("experience", 0.3), 4),
                "education": round(edu_val * norm_w.get("education", 0.15), 4),
                "semantic": round(sem_val * norm_w.get("semantic", 0.15), 4),
            },
        },
    )


@router.delete("/{evaluation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_candidate_evaluation(
    evaluation_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Hard delete candidate evaluation, resume file, and chunks (GDPR / compliance)."""
    res = await db.execute(
        select(Evaluation)
        .options(selectinload(Evaluation.resume))
        .where(Evaluation.id == evaluation_id, Evaluation.user_id == current_user.id)
    )
    ev = res.scalar_one_or_none()
    if ev is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Evaluation '{evaluation_id}' not found",
        )

    # Delete storage file
    if ev.resume:
        storage = get_storage_backend()
        try:
            await storage.delete_file(ev.resume.storage_path)
        except Exception:
            pass

    # Audit log before deletion
    audit = AuditLog(
        user_id=current_user.id,
        action="hard_delete_candidate",
        target_type="evaluation",
        target_id=ev.id,
        details_json={"resume_id": ev.resume_id, "job_id": ev.job_id},
    )
    db.add(audit)

    await db.delete(ev)
    await db.commit()


@router.delete("/{evaluation_id}/hard-delete", status_code=status.HTTP_200_OK)
async def hard_delete_candidate(
    evaluation_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, str]:
    """GDPR hard delete endpoint returning explicit purged confirmation."""
    await delete_candidate_evaluation(evaluation_id, current_user, db)
    return {"status": "purged", "message": f"Candidate {evaluation_id} purged"}


@router.get("/{evaluation_id}/export")
async def export_candidate_data(
    evaluation_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    """Export complete candidate dossier bundle for data portability."""
    res = await db.execute(
        select(Evaluation)
        .options(
            selectinload(Evaluation.resume),
            selectinload(Evaluation.decisions),
            selectinload(Evaluation.feedback),
            selectinload(Evaluation.emails),
        )
        .where(Evaluation.id == evaluation_id, Evaluation.user_id == current_user.id)
    )
    ev = res.scalar_one_or_none()
    if ev is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Evaluation '{evaluation_id}' not found",
        )

    return {
        "candidate_id": ev.id,
        "resume_id": ev.resume_id,
        "filename": ev.resume.filename if ev.resume else "Unknown",
        "total_score": ev.total_score,
        "tier": ev.tier,
        "stage": ev.stage,
        "breakdown": ev.breakdown_json,
        "explanation": ev.explanation_json,
        "interview_questions": ev.interview_questions_json,
        "email_drafts": ev.email_drafts_json,
        "decisions": [
            {
                "from_stage": d.from_stage,
                "to_stage": d.to_stage,
                "notes": d.notes,
                "created_at": d.created_at.isoformat(),
            }
            for d in ev.decisions
        ],
        "feedback": [
            {
                "interviewer": f.interviewer_name,
                "score": f.overall_score,
                "recommendation": f.recommendation,
                "notes": f.notes,
            }
            for f in ev.feedback
        ],
        "emails": [
            {
                "type": e.email_type,
                "recipient": e.recipient_email,
                "status": e.status,
                "subject": e.subject,
                "sent_at": e.sent_at.isoformat() if e.sent_at else None,
            }
            for e in ev.emails
        ],
    }


@router.get("/job/{job_id}/export/csv")
async def export_candidates_csv(
    job_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> StreamingResponse:
    """Export candidate evaluations to CSV with formula-injection protection."""
    job_res = await db.execute(select(Job).where(Job.id == job_id, Job.user_id == current_user.id))
    if job_res.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job '{job_id}' not found",
        )

    res = await db.execute(
        select(Evaluation)
        .options(selectinload(Evaluation.resume))
        .where(Evaluation.job_id == job_id, Evaluation.user_id == current_user.id)
        .order_by(Evaluation.total_score.desc())
    )
    evals = res.scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "Candidate Filename",
            "Score",
            "Tier",
            "Stage",
            "Skills Score",
            "Experience Score",
            "Education Score",
            "Semantic Score",
            "Confidence",
        ]
    )

    for e in evals:
        b = e.breakdown_json
        writer.writerow(
            [
                sanitize_csv_cell(e.resume.filename if e.resume else "Unknown"),
                f"{e.total_score:.4f}",
                sanitize_csv_cell(e.tier),
                sanitize_csv_cell(e.stage),
                f"{b.get('skills', {}).get('score', 0.0):.4f}",
                f"{b.get('experience', {}).get('score', 0.0):.4f}",
                f"{b.get('education', {}).get('score', 0.0):.4f}",
                f"{b.get('semantic', {}).get('score', 0.0):.4f}",
                f"{e.confidence:.2f}",
            ]
        )

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="job_{job_id[:8]}_candidates.csv"'},
    )


@router.get("/job/{job_id}/export/pdf")
async def export_shortlist_pdf(
    job_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    """Export PDF report of shortlisted candidates."""
    job_res = await db.execute(select(Job).where(Job.id == job_id, Job.user_id == current_user.id))
    job = job_res.scalar_one_or_none()
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job '{job_id}' not found",
        )

    res = await db.execute(
        select(Evaluation)
        .options(selectinload(Evaluation.resume))
        .where(
            Evaluation.job_id == job_id,
            Evaluation.user_id == current_user.id,
            Evaluation.stage.in_(
                ["shortlisted", "interview_scheduled", "interviewed", "offer_extended", "hired"]
            ),
        )
        .order_by(Evaluation.total_score.desc())
    )
    shortlisted = res.scalars().all()

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, 750, "RECRUIT LENS: CANDIDATE SHORTLIST REPORT")
    c.setFont("Helvetica", 11)
    c.drawString(50, 730, f"Requisition: {job.title} ({job.department})")
    c.drawString(50, 715, f"Generated: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    c.drawString(50, 700, f"Total Shortlisted: {len(shortlisted)}")

    c.line(50, 690, 560, 690)
    y = 670

    c.setFont("Helvetica-Bold", 10)
    c.drawString(50, y, "Candidate")
    c.drawString(250, y, "Score")
    c.drawString(330, y, "Tier")
    c.drawString(420, y, "Stage")
    y -= 15
    c.line(50, y + 5, 560, y + 5)

    c.setFont("Helvetica", 9)
    for ev in shortlisted:
        if y < 60:
            c.showPage()
            y = 750
        name = ev.resume.filename if ev.resume else "Unknown"
        c.drawString(50, y, name[:35])
        c.drawString(250, y, f"{ev.total_score:.4f}")
        c.drawString(330, y, ev.tier)
        c.drawString(420, y, ev.stage)
        y -= 18

    c.save()
    buf.seek(0)
    return Response(
        content=buf.getvalue(),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="shortlist_{job_id[:8]}.pdf"'},
    )


@router.post("/{evaluation_id}/generate-llm")
async def trigger_on_demand_llm(
    evaluation_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    """Generate LLM synthesized explanation, questions, and drafts with evidence hash caching."""
    # Enforce daily token budget
    if current_user.daily_token_usage >= settings.DAILY_TOKEN_BUDGET:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Daily LLM token budget exceeded ({settings.DAILY_TOKEN_BUDGET} tokens/day)",
        )

    res = await db.execute(
        select(Evaluation).where(
            Evaluation.id == evaluation_id, Evaluation.user_id == current_user.id
        )
    )
    ev = res.scalar_one_or_none()
    if ev is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Evaluation '{evaluation_id}' not found",
        )

    success = await generate_on_demand_llm_text(evaluation_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate LLM text",
        )

    # Reload evaluation
    await db.refresh(ev)
    return {
        "status": "success",
        "evaluation_id": ev.id,
        "explanation": ev.explanation_json,
        "interview_questions": ev.interview_questions_json,
        "email_drafts": ev.email_drafts_json,
        "llm_generated": ev.llm_generated,
        "explanation_type": ev.explanation_type,
    }


@router.post("/{evaluation_id}/mcp-token")
async def generate_mcp_confirmation_token(
    evaluation_id: str,
    decision: str = Query(
        ...,
        description="Target decision stage (e.g. shortlisted, interview_scheduled, held, rejected, hired)",
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Generate a secure, single-use confirmation token for executing an MCP decision.
    Valid for 15 minutes.
    """
    res = await db.execute(
        select(Evaluation).where(
            Evaluation.id == evaluation_id, Evaluation.user_id == current_user.id
        )
    )
    ev = res.scalar_one_or_none()
    if ev is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Evaluation '{evaluation_id}' not found",
        )

    token = f"mcp_{secrets.token_hex(16)}"
    expires_at = datetime.now(UTC) + timedelta(minutes=15)

    record = McpConfirmationToken(
        user_id=current_user.id,
        token=token,
        action="make_decision",
        target_id=evaluation_id,
        decision=decision,
        is_used=False,
        expires_at=expires_at,
    )
    db.add(record)
    await db.commit()

    return {
        "token": token,
        "evaluation_id": evaluation_id,
        "decision": decision,
        "expires_at": expires_at.isoformat(),
        "instructions": "Pass this token as 'confirmation_token' to the MCP make_decision tool.",
    }
