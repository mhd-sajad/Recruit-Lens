"""SQLAlchemy database models for Recruit Lens multi-tenant architecture."""

from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.db.base import Base, TenantScopedMixin, TimestampMixin, generate_uuid, utc_now

# Use JSON with SQLite fallback
JSON_TYPE = JSON().with_variant(SQLiteJSON, "sqlite")


class Tenant(Base, TimestampMixin):
    """Organization/Company tenant for strict multi-tenant data isolation."""

    __tablename__ = "tenants"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    users: Mapped[list["User"]] = relationship(
        "User", back_populates="tenant", cascade="all, delete-orphan"
    )
    jobs: Mapped[list["Job"]] = relationship(
        "Job", back_populates="tenant", cascade="all, delete-orphan"
    )


class User(Base, TenantScopedMixin, TimestampMixin):
    """User account associated with a specific tenant."""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    tenant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tenants.id", ondelete="CASCADE"), index=True, nullable=False
    )
    email: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    role: Mapped[str] = mapped_column(
        String(50), default="recruiter", nullable=False
    )  # admin, recruiter, reviewer
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="users")

    __table_args__ = (UniqueConstraint("tenant_id", "email", name="uq_user_tenant_email"),)


class Job(Base, TenantScopedMixin, TimestampMixin):
    """Job requisition / job description posting."""

    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    tenant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tenants.id", ondelete="CASCADE"), index=True, nullable=False
    )
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

    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="jobs")
    resumes: Mapped[list["Resume"]] = relationship(
        "Resume", back_populates="job", cascade="all, delete-orphan"
    )
    evaluations: Mapped[list["Evaluation"]] = relationship(
        "Evaluation", back_populates="job", cascade="all, delete-orphan"
    )


class Resume(Base, TenantScopedMixin, TimestampMixin):
    """Uploaded candidate resume document associated with a specific job requisition."""

    __tablename__ = "resumes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    tenant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tenants.id", ondelete="CASCADE"), index=True, nullable=False
    )
    job_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("jobs.id", ondelete="CASCADE"), index=True, nullable=False
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_hash: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    status: Mapped[str] = mapped_column(
        String(50), default="uploaded", nullable=False, index=True
    )  # uploaded, parsed, scored, failed
    parsed_data_json: Mapped[dict[str, Any]] = mapped_column(
        JSON_TYPE, default=dict, nullable=False
    )

    job: Mapped["Job"] = relationship("Job", back_populates="resumes")
    evaluation: Mapped["Evaluation | None"] = relationship(
        "Evaluation", back_populates="resume", uselist=False, cascade="all, delete-orphan"
    )
    chunks: Mapped[list["EvidenceChunkModel"]] = relationship(
        "EvidenceChunkModel", back_populates="resume", cascade="all, delete-orphan"
    )


class EvidenceChunkModel(Base, TenantScopedMixin):
    """Granular extracted text chunk with optional binary embedding representation."""

    __tablename__ = "evidence_chunks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    tenant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tenants.id", ondelete="CASCADE"), index=True, nullable=False
    )
    resume_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("resumes.id", ondelete="CASCADE"), index=True, nullable=False
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    section: Mapped[str] = mapped_column(String(100), default="experience", nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding_bytes: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)

    resume: Mapped["Resume"] = relationship("Resume", back_populates="chunks")


class Evaluation(Base, TenantScopedMixin, TimestampMixin):
    """Scored evaluation result for a candidate with explainable metrics and generated texts."""

    __tablename__ = "evaluations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    tenant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tenants.id", ondelete="CASCADE"), index=True, nullable=False
    )
    job_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("jobs.id", ondelete="CASCADE"), index=True, nullable=False
    )
    resume_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("resumes.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )

    total_score: Mapped[float] = mapped_column(Float, nullable=False, index=True)
    tier: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # Strong Fit, Interview, Hold, Reject, Abstain
    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)

    breakdown_json: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, default=dict, nullable=False)
    explanation_json: Mapped[dict[str, Any]] = mapped_column(
        JSON_TYPE, default=dict, nullable=False
    )
    questions_json: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, default=dict, nullable=False)
    email_drafts_json: Mapped[dict[str, Any]] = mapped_column(
        JSON_TYPE, default=dict, nullable=False
    )

    # Workflow decision
    decision: Mapped[str] = mapped_column(
        String(50), default="pending", nullable=False, index=True
    )  # pending, shortlisted, interviewed, held, rejected, hired
    decision_notes: Mapped[str] = mapped_column(Text, default="", nullable=False)

    # Evidence hash for content caching
    evidence_hash: Mapped[str] = mapped_column(String(64), index=True, default="", nullable=False)
    llm_generated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    job: Mapped["Job"] = relationship("Job", back_populates="evaluations")
    resume: Mapped["Resume"] = relationship("Resume", back_populates="evaluation")


class AuditLog(Base, TenantScopedMixin):
    """Immutable audit trail logging every human decision and administrative action."""

    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    tenant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tenants.id", ondelete="CASCADE"), index=True, nullable=False
    )
    user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    action: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True
    )  # candidate_decision, job_created, weight_updated, etc.
    target_type: Mapped[str] = mapped_column(String(50), nullable=False)  # evaluation, job, resume
    target_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    details_json: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
        index=True,
    )


class BackgroundTask(Base, TenantScopedMixin, TimestampMixin):
    """Persistent task tracker for batch resume ingestion and asynchronous LLM jobs."""

    __tablename__ = "background_tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    tenant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tenants.id", ondelete="CASCADE"), index=True, nullable=False
    )
    job_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True
    )
    task_type: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True
    )  # batch_ingestion, llm_generation
    status: Mapped[str] = mapped_column(
        String(50), default="pending", nullable=False, index=True
    )  # pending, processing, completed, failed, cancelled
    progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, default=dict, nullable=False)
    result_json: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, default=dict, nullable=False)
