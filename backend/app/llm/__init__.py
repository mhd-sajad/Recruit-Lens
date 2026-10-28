"""
Recruit Lens LLM & Agent Subsystem.
Evidence-grounded explanation, calibrated interviewing, professional email drafting, and Self-RAG critique.
"""

from app.llm.critique import run_critique_and_refine
from app.llm.evidence import compile_evidence_packet
from app.llm.guardrails import (
    SYSTEM_GUARDRAIL_PROMPT,
    detect_and_neutralize_injections,
    format_evidence_block,
    redact_pii_blind_mode,
)
from app.llm.orchestrator import (
    AgentExecutionRecord,
    AgentExecutionRepository,
    AgentOrchestrator,
    AgentState,
    InMemoryAgentRepository,
)
from app.llm.provider import (
    BaseLLMProvider,
    FallbackLLMProvider,
    GroqProvider,
    LLMCache,
    LLMResponse,
    NoLLMProvider,
    OllamaProvider,
    TokenBucketRateLimiter,
)
from app.llm.repair import parse_and_repair_json
from app.llm.schemas import (
    CandidateAgentResult,
    CandidateExplanation,
    CritiqueCheck,
    CritiqueResult,
    EmailDraft,
    EmailsResult,
    EvidenceChunk,
    EvidencePacket,
    InterviewQuestion,
    InterviewQuestionsResult,
)
from app.llm.templates import (
    generate_deterministic_emails,
    generate_deterministic_explanation,
    generate_deterministic_questions,
)

__all__ = [
    "AgentExecutionRecord",
    "AgentExecutionRepository",
    "AgentOrchestrator",
    "AgentState",
    "BaseLLMProvider",
    "CandidateAgentResult",
    "CandidateExplanation",
    "CritiqueCheck",
    "CritiqueResult",
    "EmailDraft",
    "EmailsResult",
    "EvidenceChunk",
    "EvidencePacket",
    "FallbackLLMProvider",
    "GroqProvider",
    "InMemoryAgentRepository",
    "InterviewQuestion",
    "InterviewQuestionsResult",
    "LLMCache",
    "LLMResponse",
    "NoLLMProvider",
    "OllamaProvider",
    "TokenBucketRateLimiter",
    "compile_evidence_packet",
    "detect_and_neutralize_injections",
    "format_evidence_block",
    "generate_deterministic_emails",
    "generate_deterministic_explanation",
    "generate_deterministic_questions",
    "parse_and_repair_json",
    "redact_pii_blind_mode",
    "run_critique_and_refine",
    "SYSTEM_GUARDRAIL_PROMPT",
]
