"""Pydantic API request and response schemas for REST endpoints."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.llm.schemas import CopilotCitation, CopilotQueryRequest, CopilotQueryResponse


class JobCreateRequest(BaseModel):
    """Job requisition creation payload."""

    title: str = Field(min_length=2, max_length=255)
    department: str = Field(default="Engineering", max_length=100)
    raw_text: str = Field(min_length=20)
    weights: dict[str, float] | None = None


class JobExtractRequirementsRequest(BaseModel):
    """Payload to extract requirements from raw job description text."""

    raw_text: str = Field(min_length=10)


class JobExtractRequirementsResponse(BaseModel):
    """Extracted structured skills, experience, and education from a job description."""

    must_have_skills: list[str] = Field(default_factory=list)
    nice_to_have_skills: list[str] = Field(default_factory=list)
    min_years_experience: float | None = None
    min_education_name: str | None = None
    suggested_weights: dict[str, float] = Field(default_factory=dict)


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
    user_id: str
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
    job_id: str
    filename: str
    file_hash: str
    status: str
    storage_backend: str
    signed_url: str | None = None
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
    stage: str
    explanation_type: str
    llm_generated: bool
    created_at: datetime


class EvaluationDetailResponse(BaseModel):
    """Comprehensive candidate dossier with scores, breakdown, explanation, questions, drafts."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    job_id: str
    resume_id: str
    candidate_filename: str
    total_score: float
    tier: str
    confidence: float
    stage: str
    breakdown: dict[str, Any]
    explanation: dict[str, Any]
    explanation_type: str
    interview_questions: dict[str, Any]
    email_drafts: dict[str, Any]
    evidence_hash: str
    llm_generated: bool
    created_at: datetime
    updated_at: datetime
    raw_text: str = ""
    citations: list[dict[str, Any]] = Field(default_factory=list)


class StageTransitionRequest(BaseModel):
    """Candidate stage workflow transition according to state machine."""

    to_stage: str = Field(
        pattern=r"^(shortlisted|interview_scheduled|interviewed|offer_extended|hired|held|rejected|declined|screened)$"
    )
    notes: str = Field(default="", max_length=2000)


class StageTransitionResponse(BaseModel):
    """Stage transition confirmation response."""

    id: str
    evaluation_id: str
    from_stage: str
    to_stage: str
    notes: str
    audit_log_id: str
    updated_at: datetime


class InterviewFeedbackCreate(BaseModel):
    """Post-interview structured scorecard submission."""

    interviewer_name: str = Field(min_length=2, max_length=255)
    overall_score: int = Field(ge=1, le=5)
    technical_rating: int = Field(default=3, ge=1, le=5)
    communication_rating: int = Field(default=3, ge=1, le=5)
    recommendation: Literal["hire", "no_hire", "strong_hire", "mixed"]
    strengths: str = Field(default="", max_length=3000)
    concerns: str = Field(default="", max_length=3000)
    notes: str = Field(default="", max_length=3000)


class InterviewFeedbackResponse(BaseModel):
    """Structured interview scorecard response."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    evaluation_id: str
    interviewer_name: str
    overall_score: int
    technical_rating: int
    communication_rating: int
    recommendation: str
    strengths: str
    concerns: str
    notes: str
    created_at: datetime


class EmailDraftResponse(BaseModel):
    """Email record representation."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    evaluation_id: str
    email_type: str
    recipient_email: str
    subject: str
    body: str
    status: str
    sent_at: datetime | None
    error_message: str | None
    created_at: datetime


class EmailUpdateRequest(BaseModel):
    """Recruiter edit to an email draft."""

    subject: str | None = None
    body: str | None = None


class EmailSendResponse(BaseModel):
    """Result of sending an email."""

    id: str
    status: str
    dry_run: bool
    sent_at: datetime
    message: str


class WhatIfRequest(BaseModel):
    """What-if sensitivity simulation request."""

    weights: dict[str, float] | None = None
    min_years_experience: float | None = None


class WhatIfResponse(BaseModel):
    """What-if calculation result without mutating database."""

    original_score: float
    new_score: float
    original_tier: str
    new_tier: str
    score_delta: float
    breakdown: dict[str, Any]


class AuditLogResponse(BaseModel):
    """Audit log event entry."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: str
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


class PipelineAnalyticsResponse(BaseModel):
    """Aggregated recruiting pipeline and diversity analytics."""

    total_candidates: int
    stage_counts: dict[str, int]
    tier_counts: dict[str, int]
    decided_count: int
    advanced_count: int
    agreement_rate_pct: float
    disclaimer: str


class UserSettingsResponse(BaseModel):
    """User UI and privacy preferences."""

    user_id: str
    email: str
    role: str
    blind_mode_enabled: bool = False
    dark_mode: bool = False
    export_anonymized: bool = False


class UserSettingsUpdate(BaseModel):
    """User settings update payload."""

    blind_mode_enabled: bool | None = None
    dark_mode: bool | None = None
    export_anonymized: bool | None = None


__all__ = [
    "CopilotCitation",
    "CopilotQueryRequest",
    "CopilotQueryResponse",
]
