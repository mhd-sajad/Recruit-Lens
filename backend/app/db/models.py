"""SQLAlchemy database models for Recruit Lens per-user architecture."""

from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.db.base import Base, TimestampMixin, UserScopedMixin, generate_uuid

# Use JSON with SQLite fallback
JSON_TYPE = JSON().with_variant(SQLiteJSON, "sqlite")


class User(Base, TimestampMixin):
    """Recruiter account with strict per-user isolation."""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    role: Mapped[str] = mapped_column(
        String(50), default="recruiter", nullable=False
    )  # admin, recruiter, reviewer
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    daily_token_usage: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_token_reset_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    jobs: Mapped[list["Job"]] = relationship(
        "Job", back_populates="user", cascade="all, delete-orphan"
    )
    refresh_tokens: Mapped[list["RefreshTokenRecord"]] = relationship(
        "RefreshTokenRecord", back_populates="user", cascade="all, delete-orphan"
    )


class RefreshTokenRecord(Base, TimestampMixin):
    """Refresh token record for rotation and theft/reuse detection."""

    __tablename__ = "refresh_tokens"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    token_family: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    is_revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="refresh_tokens")


class Job(Base, UserScopedMixin, TimestampMixin):
    """Job requisition / job description posting."""

    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    department: Mapped[str] = mapped_column(String(255), default="General", nullable=False)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    requirements_json: Mapped[dict[str, Any]] = mapped_column(
        JSON_TYPE, default=dict, nullable=False
    )
    weights_json: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(
        String(50), default="active", nullable=False, index=True
    )  # active, closed, draft

    user: Mapped["User"] = relationship("User", back_populates="jobs")
    resumes: Mapped[list["Resume"]] = relationship(
        "Resume", back_populates="job", cascade="all, delete-orphan"
    )
    evaluations: Mapped[list["Evaluation"]] = relationship(
        "Evaluation", back_populates="job", cascade="all, delete-orphan"
    )


class Resume(Base, UserScopedMixin, TimestampMixin):
    """Uploaded candidate resume document associated with a specific job requisition."""

    __tablename__ = "resumes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    job_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("jobs.id", ondelete="CASCADE"), index=True, nullable=False
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(512), nullable=False)
    storage_backend: Mapped[str] = mapped_column(String(50), default="local", nullable=False)
    file_hash: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    status: Mapped[str] = mapped_column(
        String(50), default="pending", nullable=False, index=True
    )  # pending, parsed, error
    raw_text: Mapped[str] = mapped_column(Text, default="", nullable=False)
    parse_result_json: Mapped[dict[str, Any]] = mapped_column(
        JSON_TYPE, default=dict, nullable=False
    )

    job: Mapped["Job"] = relationship("Job", back_populates="resumes")
    evaluation: Mapped["Evaluation | None"] = relationship(
        "Evaluation", back_populates="resume", uselist=False, cascade="all, delete-orphan"
    )
    chunks: Mapped[list["EvidenceChunkModel"]] = relationship(
        "EvidenceChunkModel", back_populates="resume", cascade="all, delete-orphan"
    )


class Evaluation(Base, UserScopedMixin, TimestampMixin):
    """Comprehensive evaluation record, score breakdown, and workflow stage."""

    __tablename__ = "evaluations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    job_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("jobs.id", ondelete="CASCADE"), index=True, nullable=False
    )
    resume_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("resumes.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    total_score: Mapped[float] = mapped_column(Float, nullable=False, index=True)
    tier: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # FastTrack, Review, Hold, Reject, Abstain
    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)

    # Workflow stage according to validated state machine
    stage: Mapped[str] = mapped_column(
        String(50), default="screened", nullable=False, index=True
    )  # screened, shortlisted, interview_scheduled, interviewed, offer_extended, hired, held, rejected, declined

    breakdown_json: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, default=dict, nullable=False)
    explanation_json: Mapped[dict[str, Any]] = mapped_column(
        JSON_TYPE, default=dict, nullable=False
    )
    explanation_type: Mapped[str] = mapped_column(
        String(20), default="template", nullable=False
    )  # template, llm
    interview_questions_json: Mapped[dict[str, Any]] = mapped_column(
        JSON_TYPE, default=dict, nullable=False
    )
    email_drafts_json: Mapped[dict[str, Any]] = mapped_column(
        JSON_TYPE, default=dict, nullable=False
    )
    evidence_hash: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    llm_generated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    job: Mapped["Job"] = relationship("Job", back_populates="evaluations")
    resume: Mapped["Resume"] = relationship("Resume", back_populates="evaluation")
    decisions: Mapped[list["DecisionRecord"]] = relationship(
        "DecisionRecord", back_populates="evaluation", cascade="all, delete-orphan"
    )
    feedback: Mapped[list["InterviewFeedbackRecord"]] = relationship(
        "InterviewFeedbackRecord", back_populates="evaluation", cascade="all, delete-orphan"
    )
    emails: Mapped[list["EmailRecord"]] = relationship(
        "EmailRecord", back_populates="evaluation", cascade="all, delete-orphan"
    )


class DecisionRecord(Base, TimestampMixin):
    """Append-only audit record of candidate stage transitions."""

    __tablename__ = "decisions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    evaluation_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("evaluations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    from_stage: Mapped[str] = mapped_column(String(50), nullable=False)
    to_stage: Mapped[str] = mapped_column(String(50), nullable=False)
    notes: Mapped[str] = mapped_column(Text, default="", nullable=False)

    evaluation: Mapped["Evaluation"] = relationship("Evaluation", back_populates="decisions")


class InterviewFeedbackRecord(Base, TimestampMixin):
    """Post-interview structured scorecard and recruiter feedback."""

    __tablename__ = "interview_feedback"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    evaluation_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("evaluations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    interviewer_name: Mapped[str] = mapped_column(String(255), nullable=False)
    overall_score: Mapped[int] = mapped_column(Integer, nullable=False)  # 1 to 5
    technical_rating: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    communication_rating: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    recommendation: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # hire, no_hire, strong_hire, mixed
    strengths: Mapped[str] = mapped_column(Text, default="", nullable=False)
    concerns: Mapped[str] = mapped_column(Text, default="", nullable=False)
    notes: Mapped[str] = mapped_column(Text, default="", nullable=False)

    evaluation: Mapped["Evaluation"] = relationship("Evaluation", back_populates="feedback")


class EmailRecord(Base, TimestampMixin):
    """Email draft, approval, and send tracking log with daily cap enforcement."""

    __tablename__ = "emails"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    evaluation_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("evaluations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    email_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # interview_invitation, rejection, hold_update
    recipient_email: Mapped[str] = mapped_column(String(255), nullable=False)
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(50), default="draft", nullable=False, index=True
    )  # draft, approved, sent, failed
    approved_by_user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    evaluation: Mapped["Evaluation"] = relationship("Evaluation", back_populates="emails")


class EvidenceChunkModel(Base, TimestampMixin):
    """Section-aware evidence chunk extracted from resume."""

    __tablename__ = "evidence_chunks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    resume_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("resumes.id", ondelete="CASCADE"), index=True, nullable=False
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    section: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    char_start: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    char_end: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, default=dict, nullable=False)

    resume: Mapped["Resume"] = relationship("Resume", back_populates="chunks")


class AuditLog(Base):
    """Immutable audit event log capturing all state changes and human actions."""

    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), index=True, nullable=True
    )
    action: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    target_type: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    target_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    details_json: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, default=dict, nullable=False)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False, index=True
    )


class BackgroundTask(Base, UserScopedMixin, TimestampMixin):
    """Resumable asynchronous worker task tracker."""

    __tablename__ = "background_tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    task_type: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    status: Mapped[str] = mapped_column(
        String(50), default="pending", nullable=False, index=True
    )  # pending, processing, completed, failed, cancelled
    progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, default=dict, nullable=False)
    result_json: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, default=dict, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
