"""
Tests for Self-RAG Critique module, sentence-level verification, number checking,
and deterministic fallback on ungrounded claims.
"""

import pytest

from app.llm.critique import (
    extract_citations,
    run_critique_and_refine,
    verify_numbers_and_entities,
)
from app.llm.provider import NoLLMProvider
from app.llm.schemas import (
    CandidateExplanation,
    EvidenceChunk,
    EvidencePacket,
)


def test_extract_citations() -> None:
    """Verify regex extraction of chunk IDs."""
    text1 = "Demonstrated deep expertise in Kubernetes and Docker [c_01]."
    assert extract_citations(text1) == ["c_01"]

    text2 = "Managed clusters across multiple clouds [c_01, c_02] with PostgreSQL [c_03]."
    assert extract_citations(text2) == ["c_01", "c_02", "c_03"]


def test_verify_numbers_and_entities() -> None:
    """Verify that ungrounded numerical claims are flagged."""
    chunk = "Led a team of 4 engineers and optimized database latency from 200ms to 50ms in 2023."

    # Grounded numbers: 4, 2023
    ok1, missing1 = verify_numbers_and_entities("Candidate led 4 engineers in 2023.", chunk)
    assert ok1 is True
    assert len(missing1) == 0

    # Ungrounded fabricated numbers: $15M revenue, 850% increase
    ok2, missing2 = verify_numbers_and_entities(
        "Generated $15M in revenue with 850% growth.", chunk
    )
    assert ok2 is False
    assert any("$15M" in m for m in missing2) or any("850%" in m for m in missing2)


@pytest.mark.asyncio
async def test_critique_pass_on_grounded_explanation() -> None:
    """Verify that a factually grounded explanation achieves PASS verdict."""
    chunk = EvidenceChunk(
        chunk_id="c_01",
        resume_id="cand_01",
        section="EXPERIENCE",
        text="Built distributed services in Python, Kubernetes, and Docker for 5 years.",
    )
    packet = EvidencePacket(
        candidate_id="cand_01",
        retrieved_chunks=[chunk],
        matched_must_skills=["Python", "Kubernetes"],
        years_experience=5.0,
        required_years=4.0,
        assigned_tier="Strong Fit",
    )

    explanation = CandidateExplanation(
        sentences=[
            "Built distributed services in Python, Kubernetes, and Docker for 5 years [c_01].",
            "Demonstrated 5 years of software experience building distributed systems with Python, Docker, and Kubernetes [c_01].",
        ],
        citations=[["c_01"], ["c_01"]],
        summary_text="Built distributed services in Python, Kubernetes, and Docker for 5 years [c_01].",
    )

    checked_exp, result = await run_critique_and_refine(
        explanation=explanation,
        packet=packet,
        provider=NoLLMProvider(),
    )
    assert result.verdict == "PASS"
    assert result.is_fallback is False


@pytest.mark.asyncio
async def test_critique_blocks_and_falls_back_on_hallucination() -> None:
    """Verify that an explanation with fabricated claims and numbers is BLOCKED."""
    chunk = EvidenceChunk(
        chunk_id="c_01",
        resume_id="cand_02",
        section="EXPERIENCE",
        text="Junior software intern maintaining internal documentation.",
    )
    packet = EvidencePacket(
        candidate_id="cand_02",
        retrieved_chunks=[chunk],
        matched_must_skills=[],
        missing_must_skills=["Kubernetes", "AWS"],
        years_experience=1.0,
        required_years=5.0,
        assigned_tier="Hold",
    )

    # Completely fabricated claim: invented $50M savings and false chunk citation c_99
    fabricated_explanation = CandidateExplanation(
        sentences=[
            "Candidate single-handedly built an autonomous quantum cloud [c_99].",
            "Generated $50M in immediate cost savings in 2025 [c_01].",
        ],
        citations=[["c_99"], ["c_01"]],
        summary_text="Candidate single-handedly built an autonomous quantum cloud [c_99]. Generated $50M in cost savings in 2025 [c_01].",
    )

    fallback_exp, result = await run_critique_and_refine(
        explanation=fabricated_explanation,
        packet=packet,
        provider=NoLLMProvider(),
        max_rewrites=0,
    )

    assert result.verdict == "BLOCK"
    assert result.is_fallback is True
    # Fallback explanation is safe, factual, and deterministic
    assert "Hold" in fallback_exp.summary_text
    assert "50M" not in fallback_exp.summary_text


@pytest.mark.asyncio
async def test_critique_blocks_false_numeric_claim_next_to_true_tier_statement() -> None:
    """Verify that an explanation containing a true tier statement BUT an adjacent false numeric claim is BLOCKED."""
    chunk = EvidenceChunk(
        chunk_id="c_01",
        resume_id="cand_num_01",
        section="EXPERIENCE",
        text="Software engineer working in a 4-person agile squad maintaining PostgreSQL.",
    )
    packet = EvidencePacket(
        candidate_id="cand_num_01",
        retrieved_chunks=[chunk],
        matched_must_skills=["PostgreSQL"],
        years_experience=3.0,
        required_years=3.0,
        assigned_tier="FastTrack",
    )

    # True tier statement in sentence 1, but completely fabricated 45-person team in sentence 2
    mixed_explanation = CandidateExplanation(
        sentences=[
            "Candidate is assigned to FastTrack tier based on verified requirements.",
            "Led a massive engineering organization of 45 engineers deploying PostgreSQL clusters [c_01].",
        ],
        citations=[[], ["c_01"]],
        summary_text="Candidate is assigned to FastTrack tier based on verified requirements. Led a massive engineering organization of 45 engineers deploying PostgreSQL clusters [c_01].",
    )

    fallback_exp, result = await run_critique_and_refine(
        explanation=mixed_explanation,
        packet=packet,
        provider=NoLLMProvider(),
        max_rewrites=0,
    )

    assert result.verdict == "BLOCK"
    assert result.is_fallback is True
    # Verify that the false number 45 is purged from the fallback
    assert "45" not in fallback_exp.summary_text
    # While the true tier remains accurately represented in fallback
    assert "FastTrack" in fallback_exp.summary_text
