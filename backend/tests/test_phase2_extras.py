"""Phase 2 Extras & Hardening Comprehensive Test Suite.

Verifies:
1. Grounded Copilot Q&A: answers with chunk citations and enforces 'not found in this resume' rule.
2. Blind Mode Guardrails: scrubs name, email, phone, and educational institutions from prompts.
3. Official MCP Server: read-only tools do not mutate, decisions require single-use, non-expired tokens.
4. Monitoring & Drift: Population Stability Index (PSI) and Kolmogorov-Smirnov (KS) calculations.
"""

from datetime import UTC, datetime, timedelta

import numpy as np
import pytest
from sqlalchemy import select

from app.core.models import ContactPII
from app.core.monitoring import compute_ks_drift, compute_psi
from app.db.models import (
    AuditLog,
    Evaluation,
    EvidenceChunkModel,
    Job,
    McpConfirmationToken,
    Resume,
    User,
)
from app.db.session import AsyncSessionLocal
from app.llm.copilot import answer_copilot_query
from app.llm.guardrails import redact_pii_blind_mode
from app.llm.provider import BaseLLMProvider, LLMResponse
from app.mcp.server import (
    draft_email,
    get_candidate_report,
    list_jobs,
    make_decision,
    search_candidates,
)


class MockLLMProvider(BaseLLMProvider):
    """Mock LLM Provider returning deterministic cited answers for testing."""

    def __init__(
        self, answer: str = "The candidate has 6 years of Go and Kafka experience [c_01]."
    ) -> None:
        self.answer = answer

    @property
    def provider_name(self) -> str:
        return "mock"

    async def complete(
        self,
        prompt: str,
        system_prompt: str = "",
        json_mode: bool = True,
        max_tokens: int = 1024,
        temperature: float = 0.1,
    ) -> LLMResponse:
        return LLMResponse(
            content=self.answer,
            model="mock-model",
            prompt_tokens=10,
            completion_tokens=10,
        )


@pytest.mark.asyncio
async def test_copilot_answers_with_chunk_citations() -> None:
    """Copilot answers with explicit chunk citations [c_01] when evidence exists."""
    async with AsyncSessionLocal() as db_session:
        user = User(
            id="user-copilot-test",
            email="copilot_tester@recruitlens.local",
            hashed_password="hash",
            full_name="Copilot Tester",
            role="recruiter",
            is_active=True,
        )
        db_session.add(user)

        job = Job(
            id="job-copilot-1",
            user_id=user.id,
            title="Streaming Engineer",
            department="Infra",
            raw_text="Job description for streaming engineer",
            requirements_json={},
            weights_json={},
            status="active",
        )
        db_session.add(job)

        resume = Resume(
            id="resume-copilot-1",
            user_id=user.id,
            job_id=job.id,
            filename="engineer.pdf",
            file_hash="hash123",
            status="parsed",
            storage_backend="local",
            storage_path="/tmp/engineer.pdf",
            raw_text="Alex Vance has 6 years Go distributed systems and Kafka pipeline experience.",
        )
        db_session.add(resume)
        await db_session.flush()

        chunk = EvidenceChunkModel(
            resume_id=resume.id,
            chunk_index=1,
            section="experience",
            text="Alex Vance has 6 years Go distributed systems and Kafka pipeline experience at scale.",
        )
        db_session.add(chunk)

        evaluation = Evaluation(
            id="eval-copilot-1",
            job_id=job.id,
            resume_id=resume.id,
            user_id=user.id,
            total_score=88.5,
            tier="FastTrack",
            confidence=1.0,
            stage="screened",
            evidence_hash="ev_hash_copilot_1",
        )
        db_session.add(evaluation)
        await db_session.commit()

        provider = MockLLMProvider("The candidate has 6 years of Go and Kafka experience [c_01].")
        resp = await answer_copilot_query(
            query="What Go and Kafka experience does the candidate have?",
            evaluation_id=evaluation.id,
            candidate_id=None,
            user_id=user.id,
            db=db_session,
            blind_mode=False,
            provider=provider,
        )

        assert resp.found_in_resume is True
        assert "[c_01]" in resp.answer
        assert len(resp.citations) >= 1
        assert resp.citations[0].chunk_id == "c_01"


@pytest.mark.asyncio
async def test_copilot_returns_not_found_when_evidence_missing() -> None:
    """Copilot returns strict 'Information not found in this resume' when query concepts are absent."""
    async with AsyncSessionLocal() as db_session:
        user = User(
            id="user-copilot-absent",
            email="absent_tester@recruitlens.local",
            hashed_password="hash",
            full_name="Absent Tester",
            role="recruiter",
            is_active=True,
        )
        db_session.add(user)

        job = Job(
            id="job-copilot-absent",
            user_id=user.id,
            title="Frontend Specialist",
            department="UI",
            raw_text="Frontend UI role",
            requirements_json={},
            weights_json={},
            status="active",
        )
        db_session.add(job)

        resume = Resume(
            id="resume-copilot-absent",
            user_id=user.id,
            job_id=job.id,
            filename="frontend.pdf",
            file_hash="hashabc",
            status="parsed",
            storage_backend="local",
            storage_path="/tmp/frontend.pdf",
            raw_text="Worked on CSS, React, and HTML5 layout designs.",
        )
        db_session.add(resume)
        await db_session.flush()

        chunk = EvidenceChunkModel(
            resume_id=resume.id,
            chunk_index=1,
            section="skills",
            text="Proficient in React, CSS3 animations, and Tailwind styling.",
        )
        db_session.add(chunk)

        evaluation = Evaluation(
            id="eval-copilot-absent",
            job_id=job.id,
            resume_id=resume.id,
            user_id=user.id,
            total_score=70.0,
            tier="Interview",
            confidence=1.0,
            stage="screened",
            evidence_hash="ev_hash_copilot_absent",
        )
        db_session.add(evaluation)
        await db_session.commit()

        resp = await answer_copilot_query(
            query="Does the candidate have quantum computing or Q# experience?",
            evaluation_id=evaluation.id,
            candidate_id=None,
            user_id=user.id,
            db=db_session,
            blind_mode=False,
        )

        assert resp.found_in_resume is False
        assert "Information not found in this resume" in resp.answer
        assert len(resp.citations) == 0


def test_blind_mode_scrubs_name_email_phone_institution() -> None:
    """Blind mode redaction scrubs candidate identity, email, phone, and university institutions."""
    raw_sample = (
        "Candidate Sarah Connor, email: sarah.c@cyberdyne.org, phone: (415) 555-2671. "
        "Graduated from Stanford University with a B.S. in Computer Science. "
        "Lives at 742 Evergreen Terrace. DOB: 1984-05-12. She worked as Lead Architect."
    )
    pii = ContactPII(
        name="Sarah Connor",
        email="sarah.c@cyberdyne.org",
        phone="(415) 555-2671",
        location="742 Evergreen Terrace",
    )

    redacted = redact_pii_blind_mode(
        text=raw_sample,
        pii=pii,
        redact_institutions=True,
        candidate_name="Sarah Connor",
    )

    assert "Sarah Connor" not in redacted
    assert "sarah.c@cyberdyne.org" not in redacted
    assert "(415) 555-2671" not in redacted
    assert "Stanford University" not in redacted
    assert "742 Evergreen Terrace" not in redacted
    assert "[EMAIL REDACTED]" in redacted
    assert "[PHONE REDACTED]" in redacted
    assert "[INSTITUTION REDACTED]" in redacted


@pytest.mark.asyncio
async def test_mcp_make_decision_without_token_is_rejected() -> None:
    """make_decision tool strictly fails if confirmation token is missing or invalid."""
    async with AsyncSessionLocal() as db_session:
        user = User(
            id="user-mcp-notoken",
            email="mcp_notoken@recruitlens.local",
            hashed_password="hash",
            full_name="MCP Tester",
            role="admin",
            api_key="lens_mcp_test_api_key_for_unit_tests_32char",
            is_active=True,
        )
        db_session.add(user)
        await db_session.commit()

    result = await make_decision(
        api_key="lens_mcp_test_api_key_for_unit_tests_32char",
        evaluation_id="eval-nonexistent",
        decision="shortlisted",
        confirmation_token="invalid-token-12345",
    )

    assert result["success"] is False
    assert "Confirmation token is invalid or already consumed" in result["error"]


@pytest.mark.asyncio
async def test_mcp_token_is_single_use_and_expires() -> None:
    """MCP token can only be consumed once and rejects expired tokens."""
    async with AsyncSessionLocal() as db_session:
        user = User(
            id="user-mcp-token-test",
            email="mcp_tokens@recruitlens.local",
            hashed_password="hash",
            full_name="Token Tester",
            role="admin",
            api_key="lens_mcp_test_api_key_for_tokens_valid_32c",
            is_active=True,
        )
        db_session.add(user)

        job = Job(
            id="job-mcp-tok",
            user_id=user.id,
            title="Backend Eng",
            department="Platform",
            raw_text="Job text",
            requirements_json={},
            weights_json={},
            status="active",
        )
        db_session.add(job)

        resume = Resume(
            id="resume-mcp-tok",
            user_id=user.id,
            job_id=job.id,
            filename="backend.pdf",
            file_hash="hash_mcp_tok",
            status="parsed",
            storage_backend="local",
            storage_path="/tmp/backend.pdf",
            raw_text="Backend engineer text",
        )
        db_session.add(resume)
        await db_session.flush()

        evaluation = Evaluation(
            id="eval-mcp-tok",
            job_id=job.id,
            resume_id=resume.id,
            user_id=user.id,
            total_score=85.0,
            tier="Review",
            confidence=1.0,
            stage="screened",
            evidence_hash="ev_hash_mcp_tok",
        )
        db_session.add(evaluation)

        # Valid token
        valid_token = McpConfirmationToken(
            id="tok-valid-1",
            user_id=user.id,
            token="tok_mcp_valid_token_sample",
            target_id=evaluation.id,
            action="stage_transition",
            decision="shortlisted",
            is_used=False,
            expires_at=datetime.now(UTC) + timedelta(minutes=15),
        )
        db_session.add(valid_token)

        # Expired token
        expired_token = McpConfirmationToken(
            id="tok-expired-1",
            user_id=user.id,
            token="tok_mcp_expired_token_sample",
            target_id=evaluation.id,
            action="stage_transition",
            decision="shortlisted",
            is_used=False,
            expires_at=datetime.now(UTC) - timedelta(minutes=5),
        )
        db_session.add(expired_token)
        await db_session.commit()

    # 1. Expired token attempt
    res_expired = await make_decision(
        api_key="lens_mcp_test_api_key_for_tokens_valid_32c",
        evaluation_id="eval-mcp-tok",
        decision="shortlisted",
        confirmation_token="tok_mcp_expired_token_sample",
    )
    assert res_expired["success"] is False
    assert "expired" in res_expired["error"].lower()

    # 2. First valid token attempt succeeds
    res_valid = await make_decision(
        api_key="lens_mcp_test_api_key_for_tokens_valid_32c",
        evaluation_id="eval-mcp-tok",
        decision="shortlisted",
        confirmation_token="tok_mcp_valid_token_sample",
    )
    assert res_valid["success"] is True
    assert res_valid["new_stage"] == "shortlisted"

    # 3. Second attempt with same token fails (single-use enforced)
    res_reused = await make_decision(
        api_key="lens_mcp_test_api_key_for_tokens_valid_32c",
        evaluation_id="eval-mcp-tok",
        decision="shortlisted",
        confirmation_token="tok_mcp_valid_token_sample",
    )
    assert res_reused["success"] is False
    assert "already consumed" in res_reused["error"]


@pytest.mark.asyncio
async def test_mcp_read_only_tools_cannot_mutate() -> None:
    """Read-only tools (list_jobs, search_candidates, get_candidate_report, draft_email) never modify DB state."""
    async with AsyncSessionLocal() as db_session:
        user = User(
            id="user-mcp-readonly",
            email="mcp_ro@recruitlens.local",
            hashed_password="hash",
            full_name="Read Only Tester",
            role="recruiter",
            api_key="lens_mcp_test_api_key_for_readonly_32char",
            is_active=True,
        )
        db_session.add(user)

        job = Job(
            id="job-mcp-ro",
            user_id=user.id,
            title="SRE",
            department="Reliability",
            raw_text="SRE description",
            requirements_json={},
            weights_json={},
            status="active",
        )
        db_session.add(job)

        resume = Resume(
            id="resume-mcp-ro",
            user_id=user.id,
            job_id=job.id,
            filename="sre.pdf",
            file_hash="hash_mcp_ro",
            status="parsed",
            storage_backend="local",
            storage_path="/tmp/sre.pdf",
            raw_text="SRE candidate text",
        )
        db_session.add(resume)
        await db_session.flush()

        evaluation = Evaluation(
            id="eval-mcp-ro",
            job_id=job.id,
            resume_id=resume.id,
            user_id=user.id,
            total_score=92.0,
            tier="FastTrack",
            confidence=1.0,
            stage="screened",
            evidence_hash="ev_hash_mcp_ro",
        )
        db_session.add(evaluation)
        await db_session.commit()

        audit_count_before = len((await db_session.execute(select(AuditLog))).scalars().all())

    # Call all read-only tools
    jobs_res = await list_jobs(api_key="lens_mcp_test_api_key_for_readonly_32char")
    assert len(jobs_res) >= 1
    assert jobs_res[0]["job_id"] == "job-mcp-ro"

    search_res = await search_candidates(
        api_key="lens_mcp_test_api_key_for_readonly_32char", job_id="job-mcp-ro"
    )
    assert len(search_res) >= 1

    report_res = await get_candidate_report(
        api_key="lens_mcp_test_api_key_for_readonly_32char", evaluation_id="eval-mcp-ro"
    )
    assert report_res["evaluation_id"] == "eval-mcp-ro"

    email_res = await draft_email(
        api_key="lens_mcp_test_api_key_for_readonly_32char", evaluation_id="eval-mcp-ro"
    )
    assert email_res["status"] == "draft"

    async with AsyncSessionLocal() as db_session:
        audit_count_after = len((await db_session.execute(select(AuditLog))).scalars().all())
    # No new audit logs or database mutation should be generated by read-only calls
    assert audit_count_after == audit_count_before


def test_psi_calculation_against_known_inputs() -> None:
    """Population Stability Index (PSI) computes expected drift values against known distributions."""
    np.random.seed(42)
    # 1. Identical distributions -> PSI near 0
    baseline = np.random.normal(loc=70, scale=10, size=1000)
    current_identical = np.random.normal(loc=70, scale=10, size=1000)
    psi_identical = compute_psi(baseline, current_identical, num_bins=10)
    assert psi_identical < 0.10, f"Expected stable PSI < 0.10, got {psi_identical}"

    # 2. Significantly shifted distribution -> PSI >= 0.25
    current_drifted = np.random.normal(loc=55, scale=12, size=1000)
    psi_drifted = compute_psi(baseline, current_drifted, num_bins=10)
    assert psi_drifted > 0.25, f"Expected drifted PSI > 0.25, got {psi_drifted}"

    # 3. Empty input handling
    assert compute_psi([], [1.0, 2.0]) == 0.0


def test_ks_drift_against_known_inputs() -> None:
    """Kolmogorov-Smirnov (KS) test accurately detects statistical drift against known distributions."""
    np.random.seed(42)
    # 1. Same distribution -> drift_detected is False (p_value > 0.05)
    sample_a = np.random.normal(loc=75, scale=8, size=500)
    sample_b = np.random.normal(loc=75, scale=8, size=500)
    res_stable = compute_ks_drift(sample_a, sample_b)
    assert res_stable["drift_detected"] is False
    assert res_stable["p_value"] > 0.05

    # 2. Shifted distribution -> drift_detected is True (p_value < 0.05)
    sample_drifted = np.random.normal(loc=60, scale=8, size=500)
    res_drifted = compute_ks_drift(sample_a, sample_drifted)
    assert res_drifted["drift_detected"] is True
    assert res_drifted["p_value"] < 0.01
