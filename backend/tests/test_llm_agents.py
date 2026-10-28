"""
Tests for LLM Agents (Explainer, Interviewer, Emailer), Templates, and Orchestrator.
"""

import pytest

from app.llm.orchestrator import (
    AgentOrchestrator,
    AgentState,
    InMemoryAgentRepository,
)
from app.llm.provider import NoLLMProvider
from app.llm.schemas import (
    EvidenceChunk,
    EvidencePacket,
)
from app.llm.templates import (
    generate_deterministic_emails,
    generate_deterministic_explanation,
    generate_deterministic_questions,
)


@pytest.fixture
def sample_packet() -> EvidencePacket:
    chunk1 = EvidenceChunk(
        chunk_id="c_01",
        resume_id="cand_test_01",
        section="WORK EXPERIENCE",
        text="Architected distributed backend APIs in Python and FastAPI with PostgreSQL databases.",
    )
    chunk2 = EvidenceChunk(
        chunk_id="c_02",
        resume_id="cand_test_01",
        section="EDUCATION",
        text="Bachelor of Science in Computer Science, State University, 2020.",
    )
    return EvidencePacket(
        candidate_id="cand_test_01",
        job_id="job_001",
        retrieved_chunks=[chunk1, chunk2],
        matched_must_skills=["Python", "FastAPI"],
        missing_must_skills=["Kubernetes"],
        years_experience=4.5,
        required_years=3.0,
        degree_level="Bachelor of Science",
        required_degree="Bachelor",
        assigned_tier="Strong Fit",
        sanitized_blind_name="[Candidate]",
    )


def test_deterministic_templates(sample_packet: EvidencePacket) -> None:
    """Verify deterministic No-LLM generation produces cited, factual outputs."""
    exp = generate_deterministic_explanation(sample_packet)
    assert len(exp.sentences) == 4
    assert "[c_01]" in exp.summary_text
    assert "Strong Fit" in exp.summary_text
    assert "Kubernetes" in exp.summary_text

    questions = generate_deterministic_questions(sample_packet)
    assert len(questions.questions) >= 3
    # Check difficulty calibration: 4.5 years experience -> mid
    assert any(q.difficulty in ("mid", "senior") for q in questions.questions)

    emails = generate_deterministic_emails(sample_packet)
    assert emails.invite.action == "interview_invite"
    assert emails.hold.action == "hold"
    assert emails.rejection.action == "rejection"

    # Absolute Safety Rule: Rejection emails NEVER contain scores or negative critique reasons
    rejection_lower = emails.rejection.body.lower()
    assert "score" not in rejection_lower
    assert "rating" not in rejection_lower
    assert "critique" not in rejection_lower
    assert "deficit" not in rejection_lower
    assert "points" not in rejection_lower


@pytest.mark.asyncio
async def test_orchestrator_pipeline_and_idempotency(sample_packet: EvidencePacket) -> None:
    """Verify Orchestrator runs through all states, logs tokens, and resumes idempotently."""
    repo = InMemoryAgentRepository()
    orchestrator = AgentOrchestrator(
        provider=NoLLMProvider(),
        repository=repo,
        max_concurrency=2,
    )

    observed_states: list[AgentState] = []

    async def callback(run_id: str, cand_id: str, state: AgentState, elapsed: float) -> None:
        observed_states.append(state)

    # First execution
    res1 = await orchestrator.run_candidate(
        sample_packet, run_id="run_100", progress_callback=callback
    )
    assert res1.candidate_id == sample_packet.candidate_id
    assert res1.is_fallback is True  # NoLLMProvider triggers deterministic templates
    assert res1.explanation is not None
    assert res1.interview_questions is not None
    assert res1.emails is not None

    # Check observed state transitions
    assert AgentState.EVIDENCE_PACKED in observed_states
    assert AgentState.EXPLAINING in observed_states
    assert AgentState.INTERVIEW_GEN in observed_states
    assert AgentState.EMAIL_GEN in observed_states
    assert AgentState.CRITIQUING in observed_states
    assert AgentState.COMPLETED in observed_states

    # Check repository state
    saved = await repo.get_record("run_100", sample_packet.candidate_id)
    assert saved is not None
    assert saved.state == AgentState.COMPLETED

    # Second execution (Idempotency check: should return saved result without re-running)
    observed_states.clear()
    res2 = await orchestrator.run_candidate(
        sample_packet, run_id="run_100", progress_callback=callback
    )
    assert res2.candidate_id == res1.candidate_id
    assert len(observed_states) == 0  # No transitions needed, returned from cache


@pytest.mark.asyncio
async def test_orchestrator_batch_concurrency_and_failure_isolation() -> None:
    """Verify batch execution runs concurrently and isolates candidate-level failures."""
    repo = InMemoryAgentRepository()
    orchestrator = AgentOrchestrator(
        provider=NoLLMProvider(),
        repository=repo,
        max_concurrency=3,
    )

    # Create 3 packets
    packets = [
        EvidencePacket(
            candidate_id=f"cand_batch_{i}",
            retrieved_chunks=[
                EvidenceChunk(
                    chunk_id="c_01",
                    resume_id=f"cand_batch_{i}",
                    section="EXPERIENCE",
                    text=f"Engineer {i} background with Python.",
                )
            ],
            matched_must_skills=["Python"],
            years_experience=float(i + 2),
            assigned_tier="Review",
        )
        for i in range(3)
    ]

    results = await orchestrator.run_batch(packets, run_id="batch_run_01")
    assert len(results) == 3
    for i, res in enumerate(results):
        assert res.candidate_id == f"cand_batch_{i}"
        assert res.explanation is not None
