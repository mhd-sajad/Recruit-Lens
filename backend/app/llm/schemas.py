"""
Structured schemas and domain models for evidence-grounded LLM agents.
Enforces typed inputs, evidence packet representations, and structured agent outputs.
"""

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


class EvidenceChunk(BaseModel):
    """Section-aware evidence chunk extracted from resume."""

    chunk_id: str = Field(description="Unique identifier for chunk within candidate evidence")
    resume_id: str
    section: str = Field(description="Normalized section name e.g. WORK EXPERIENCE, SKILLS")
    text: str = Field(description="Verbatim chunk text snippet")
    char_start: int = Field(default=0, description="Start character offset in full resume text")
    char_end: int = Field(default=0, description="End character offset in full resume text")
    metadata: dict[str, Any] = Field(default_factory=dict)


class EvidencePacket(BaseModel):
    """Strictly bounded packet of factual evidence supplied to LLM agents."""

    candidate_id: str
    job_id: str | None = None
    retrieved_chunks: list[EvidenceChunk] = Field(
        default_factory=list, description="Top-K evidence chunks relevant to requirements"
    )
    matched_must_skills: list[str] = Field(default_factory=list)
    missing_must_skills: list[str] = Field(default_factory=list)
    matched_nice_skills: list[str] = Field(default_factory=list)
    years_experience: float = 0.0
    required_years: float = 0.0
    degree_level: str = "Unknown"
    required_degree: str = "Unknown"
    assigned_tier: str = "Review"
    sanitized_blind_name: str = "[Candidate]"
    injection_detected: bool = False


class CandidateExplanation(BaseModel):
    """Structured, evidence-grounded candidate evaluation statement."""

    sentences: list[str] = Field(
        min_length=1,
        max_length=6,
        description="3 to 4 concise sentences explaining candidate fit, matched skills, and deficits",
    )
    citations: list[list[str]] = Field(
        default_factory=list,
        description="List of cited chunk IDs corresponding to each sentence e.g. [['c_01'], ['c_02']]",
    )
    summary_text: str = Field(
        default="",
        description="Full explanatory statement with inline citations e.g. [c_01]",
    )

    @model_validator(mode="before")
    @classmethod
    def normalize_explanation(cls, data: Any) -> Any:
        if isinstance(data, dict):
            import re

            if "sentences" not in data:
                text = str(data.get("explanation") or data.get("summary") or data.get("text") or "")
                raw_sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
                data["sentences"] = raw_sentences if raw_sentences else [text]
                data["summary_text"] = text
            if "summary_text" not in data and "sentences" in data:
                data["summary_text"] = " ".join(data["sentences"])
            if ("citations" not in data or not data["citations"]) and "sentences" in data:
                pat = re.compile(r"\[(c_\d{2}(?:,\s*c_\d{2})*)\]")
                cites = []
                for s in data["sentences"]:
                    found = []
                    for m in pat.findall(s):
                        found.extend([cid.strip() for cid in m.split(",") if cid.strip()])
                    cites.append(found)
                data["citations"] = cites
        return data


class InterviewQuestion(BaseModel):
    """Seniority-calibrated interview question probing a skill or gap."""

    question: str = Field(description="The interview question text")
    target_topic: str = Field(description="Specific skill or gap targeted")
    difficulty: Literal["junior", "mid", "senior"] = Field(
        description="Calibrated technical difficulty level"
    )
    rationale: str = Field(description="Why this question is relevant to this candidate")
    citation: str | None = Field(
        default=None, description="Chunk ID grounding the question if verifying claimed experience"
    )


class InterviewQuestionsResult(BaseModel):
    """Collection of calibrated interview questions."""

    questions: list[InterviewQuestion] = Field(
        min_length=1,
        max_length=6,
        description="3 to 5 tailored interview questions",
    )

    @model_validator(mode="before")
    @classmethod
    def normalize_questions(cls, data: Any) -> Any:
        if isinstance(data, list):
            return {"questions": data}
        if isinstance(data, dict) and "questions" not in data:
            for k in ["interview_questions", "items", "data"]:
                if k in data and isinstance(data[k], list):
                    data["questions"] = data[k]
                    break
        return data


class EmailDraft(BaseModel):
    """Personalized candidate communication draft."""

    action: Literal["interview_invite", "hold", "rejection"]
    subject: str = Field(description="Email subject line")
    body: str = Field(
        description="Email body text. Grounded only in verified strengths. Rejection has no internal scores."
    )
    citations_used: list[str] = Field(
        default_factory=list, description="Chunk IDs referenced in personalization"
    )


class EmailsResult(BaseModel):
    """Complete set of action-specific email drafts."""

    invite: EmailDraft
    hold: EmailDraft
    rejection: EmailDraft

    @model_validator(mode="before")
    @classmethod
    def normalize_emails(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "emails" in data and isinstance(data["emails"], dict):
                return data["emails"]
        return data


class CritiqueCheck(BaseModel):
    """Sentence-level grounding verification record."""

    sentence_index: int
    sentence: str
    cited_chunk_ids: list[str]
    is_supported: bool
    similarity_score: float = 0.0
    failure_reason: str | None = None
    unsupported_entities_or_numbers: list[str] = Field(default_factory=list)


class CritiqueResult(BaseModel):
    """Self-RAG verification evaluation outcome."""

    verdict: Literal["PASS", "REWRITE", "BLOCK"]
    checks: list[CritiqueCheck] = Field(default_factory=list)
    rewrite_count: int = 0
    rewritten_summary: str | None = None
    is_fallback: bool = False
    critique_notes: str = ""


class CandidateAgentResult(BaseModel):
    """Consolidated generation result across all agents for a single candidate."""

    candidate_id: str
    explanation: CandidateExplanation
    interview_questions: InterviewQuestionsResult
    emails: EmailsResult
    critique: CritiqueResult
    is_fallback: bool = False
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cached_tokens: int = 0
    latency_ms: float = 0.0
    injection_detected: bool = False
