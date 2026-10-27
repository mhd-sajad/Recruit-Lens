"""Data models for resume parsing, extraction, and ingestion."""

from typing import Any, Literal

from pydantic import BaseModel, Field


class ContactPII(BaseModel):
    """Personal Identifiable Information extracted from candidate documents."""

    name: str | None = None
    email: str | None = None
    phone: str | None = None
    links: list[str] = Field(default_factory=list)
    location: str | None = None


class WorkExperienceEntry(BaseModel):
    """Structured work experience record."""

    title: str | None = None
    company: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    is_current: bool = False
    bullets: list[str] = Field(default_factory=list)
    raw_text: str = ""


class EducationEntry(BaseModel):
    """Structured education history entry."""

    degree: str | None = None
    institution: str | None = None
    field_of_study: str | None = None
    graduation_year: int | None = None
    ordinal_rank: int = 0  # 0=High School, 1=Associate, 2=Bachelor, 3=Master, 4=Doctorate
    raw_text: str = ""


class ResumeParseResult(BaseModel):
    """Unified result produced by PDF parser."""

    resume_id: str
    is_resume: bool
    gate_confidence: float
    gate_signals: dict[str, bool]
    parse_confidence: float
    page_count: int
    layout_type: Literal["single_column", "multi_column", "unknown"]
    pii: ContactPII
    scoring_text: str
    raw_text: str
    sections: dict[str, str]
    experiences: list[WorkExperienceEntry]
    educations: list[EducationEntry]
    skills: list[str]


class JDScrapeResult(BaseModel):
    """Result produced by SSRF-safe JD scraper."""

    url: str
    domain: str
    title: str | None = None
    company: str | None = None
    clean_text: str
    word_count: int


class ResumeChunk(BaseModel):
    """Section-aware chunk extracted from parsed resume for retrieval."""

    chunk_id: str
    resume_id: str
    section: str
    text: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class JDChunk(BaseModel):
    """Query chunk extracted from a job description."""

    chunk_id: str
    jd_id: str
    text: str
    metadata: dict[str, Any] = Field(default_factory=dict)
