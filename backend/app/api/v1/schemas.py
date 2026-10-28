"""Pydantic API request and response schemas for REST endpoints."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class JobCreateRequest(BaseModel):
    """Job requisition creation payload."""

    title: str = Field(min_length=2, max_length=255)
    department: str = Field(default="Engineering", max_length=100)
    raw_text: str = Field(min_length=20)
    weights: dict[str, float] | None = None


class JobUpdateRequest(BaseModel):
    """Job requisition update payload."""

    title: str | None = None
    department: str | None = None
    raw_text: str | None = None
    weights: dict[str, float] | None = None
    status: str | None = None


class JobResponse(BaseModel):
    """Job requisition response representation."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    title: str
    department: str
    raw_text: str
    requirements_json: dict[str, Any]
    weights_json: dict[str, Any]
    status: str
    created_at: datetime
    updated_at: datetime


class ResumeResponse(BaseModel):
    """Uploaded candidate resume representation."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    job_id: str
    filename: str
    file_hash: str
    status: str
    created_at: datetime


class EvaluationSummaryResponse(BaseModel):
    """Compact candidate evaluation row for ranking table and drag-and-drop board."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    resume_id: str
    job_id: str
    candidate_filename: str
    total_score: float
    tier: str
    confidence: float
    decision: str
    llm_generated: bool
    created_at: datetime


class EvaluationDetailResponse(BaseModel):
    """Comprehensive candidate dossier with scores, breakdown, explanation, questions, drafts."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    job_id: str
    resume_id: str
    candidate_filename: str
    total_score: float
    tier: str
    confidence: float
    decision: str
    decision_notes: str
    breakdown: dict[str, Any]
    explanation: dict[str, Any]
    interview_questions: dict[str, Any]
    email_drafts: dict[str, Any]
    evidence_hash: str
    llm_generated: bool
    created_at: datetime
    updated_at: datetime


class CandidateDecisionRequest(BaseModel):
    """Recruiter workflow decision action."""

    decision: str = Field(pattern=r"^(shortlisted|interviewed|held|rejected|hired)$")
    decision_notes: str = Field(default="", max_length=2000)


class CandidateDecisionResponse(BaseModel):
    """Recruiter decision response confirmation."""

    id: str
    evaluation_id: str
    decision: str
    decision_notes: str
    audit_log_id: str
    updated_at: datetime


class AuditLogResponse(BaseModel):
    """Audit log event entry."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: str
    tenant_id: str
    user_id: str | None
    action: str
    target_type: str
    target_id: str
    details: dict[str, Any] = Field(validation_alias="details_json", serialization_alias="details")
    created_at: datetime


class BackgroundTaskResponse(BaseModel):
    """Asynchronous background task progress summary."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: str
    task_type: str
    status: str
    progress: int
    total: int
    error_message: str | None
    result: dict[str, Any] = Field(validation_alias="result_json", serialization_alias="result")
    created_at: datetime
    updated_at: datetime
