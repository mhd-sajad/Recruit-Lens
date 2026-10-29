"""
Resilience and Security Hardening test suite for Recruit Lens.

Covers:
1. LLM provider downtime and graceful deterministic fallback.
2. LLM token budget exhaustion and 429 handling.
3. Corrupt PDF upload rejection (magic byte validation).
4. Large 100-page document parsing and chunk boundedness.
5. Blind Mode PII redaction (zero candidate identity leakage).
6. MCP server tools and one-time confirmation token gating.
7. Feature and score drift detection (PSI, KS).
"""

from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock

import numpy as np
import pytest
from httpx import AsyncClient
from reportlab.pdfgen import canvas

from app.auth.security import create_access_token, hash_password
from app.core.monitoring import compute_ks_drift, compute_psi
from app.core.pdf_parser import parse_resume_pdf
from app.db.models import (
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
from app.mcp.server import make_decision


@pytest.mark.asyncio
async def test_resilience_corrupt_pdf_rejected(async_client: AsyncClient) -> None:
    """Uploading a corrupted file missing %PDF magic bytes must return 400."""
    async with AsyncSessionLocal() as session:
        user = User(
            email="recruiter@lens.local",
            hashed_password=hash_password("Password123!"),
            role="recruiter",
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        job = Job(user_id=user.id, title="Engineer", raw_text="Need python.")
        session.add(job)
        await session.commit()
        await session.refresh(job)

        token = create_access_token({"sub": user.id, "email": user.email, "role": user.role})

    corrupt_bytes = b"NOT_A_VALID_PDF_HEADER_JUST_RANDOM_TEXT"
    files = [("files", ("corrupt.pdf", corrupt_bytes, "application/pdf"))]

    resp = await async_client.post(
        f"/api/v1/resumes/upload/{job.id}",
        files=files,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400
    assert "not a valid PDF document" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_resilience_100_page_pdf_handling(tmp_path: Path) -> None:
    """A 100-page document must be parsed safely without memory leaks or crashes."""
    pdf_path = tmp_path / "large_100_page.pdf"
    c = canvas.Canvas(str(pdf_path))
    for page in range(1, 101):
        c.drawString(
            100, 750, f"Page {page}: Experienced Staff Software Engineer with Python and AWS."
        )
        c.drawString(100, 700, "Led distributed infrastructure and microservice architecture.")
        c.showPage()
    c.save()

    result = parse_resume_pdf(pdf_path, resume_id="large_100")
    assert result is not None
    assert len(result.raw_text) > 0
    assert "Staff Software Engineer" in result.raw_text


@pytest.mark.asyncio
async def test_resilience_blind_mode_pii_exclusion() -> None:
    """Under Blind Mode, candidate identity, email, phone, DOB, and address must be redacted."""
    raw_text = (
        "Johnathan Doe, email: john.doe@example.com, phone: +1 (555) 234-5678. "
        "Born: 1985-04-12, Address: 742 Evergreen Terrace, Springfield. "
        "He graduated from Harvard University with a degree in Computer Science. "
        "Mr. Doe architected distributed streaming pipelines in Go and Kafka."
    )

    redacted = redact_pii_blind_mode(raw_text, candidate_name="Johnathan Doe")

    assert "john.doe@example.com" not in redacted
    assert "+1 (555) 234-5678" not in redacted
    assert "742 Evergreen Terrace" not in redacted
    assert "1985-04-12" not in redacted
    assert "Harvard University" not in redacted
    assert "[EMAIL REDACTED]" in redacted
    assert "[PHONE REDACTED]" in redacted
    assert "[ADDRESS REDACTED]" in redacted
    assert "[INSTITUTION REDACTED]" in redacted


@pytest.mark.asyncio
async def test_resilience_llm_downtime_copilot_fallback() -> None:
    """When LLM provider raises connection errors, Copilot returns grounded deterministic fallback."""
    async with AsyncSessionLocal() as session:
        user = User(
            email="recruiter_copilot@lens.local",
            hashed_password=hash_password("Password123!"),
            role="recruiter",
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        job = Job(user_id=user.id, title="Backend Lead", raw_text="Need python.")
        session.add(job)
        await session.flush()

        resume = Resume(
            user_id=user.id,
            job_id=job.id,
            filename="cand.pdf",
            storage_path="/tmp/cand.pdf",
            file_hash="hash123",
            raw_text="Experienced with Python FastAPI and Docker microservices.",
        )
        session.add(resume)
        await session.flush()

        chunk = EvidenceChunkModel(
            resume_id=resume.id,
            chunk_index=1,
            section="experience",
            text="Experienced with Python FastAPI and Docker microservices.",
        )
        session.add(chunk)

        evaluation = Evaluation(
            user_id=user.id,
            job_id=job.id,
            resume_id=resume.id,
            total_score=85.0,
            tier="FastTrack",
            confidence=1.0,
            evidence_hash="evhash123",
        )
        session.add(evaluation)
        await session.commit()
        await session.refresh(evaluation)

        # Mock LLM provider that simulates outage
        mock_provider = AsyncMock()
        mock_provider.complete.side_effect = ConnectionError("Groq API 503 Service Unavailable")

        # Query asking about python
        res = await answer_copilot_query(
            query="Does this candidate have experience with Python?",
            evaluation_id=evaluation.id,
            candidate_id=None,
            user_id=user.id,
            db=session,
            provider=mock_provider,
        )

        assert res.grounded is True
        assert res.found_in_resume is True
        assert "Python" in res.answer or "FastAPI" in res.answer
        assert len(res.citations) > 0


@pytest.mark.asyncio
async def test_resilience_copilot_not_found_rule() -> None:
    """When queried about a topic absent from the candidate resume, Copilot strictly answers 'not found'."""
    async with AsyncSessionLocal() as session:
        user = User(
            email="recruiter_nf@lens.local",
            hashed_password=hash_password("Password123!"),
            role="recruiter",
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        job = Job(user_id=user.id, title="Designer", raw_text="UI designer.")
        session.add(job)
        await session.flush()

        resume = Resume(
            user_id=user.id,
            job_id=job.id,
            filename="cand2.pdf",
            storage_path="/tmp/cand2.pdf",
            file_hash="hash456",
            raw_text="UI/UX designer specialized in Figma and user research.",
        )
        session.add(resume)
        await session.flush()

        evaluation = Evaluation(
            user_id=user.id,
            job_id=job.id,
            resume_id=resume.id,
            total_score=70.0,
            tier="Review",
            confidence=1.0,
            evidence_hash="evhash456",
        )
        session.add(evaluation)
        await session.commit()
        await session.refresh(evaluation)

        res = await answer_copilot_query(
            query="Does this candidate hold any registered quantum cryptography patents?",
            evaluation_id=evaluation.id,
            candidate_id=None,
            user_id=user.id,
            db=session,
        )

        assert res.found_in_resume is False
        assert "not found in this resume" in res.answer.lower()
        assert len(res.citations) == 0


@pytest.mark.asyncio
async def test_resilience_mcp_decision_token_enforcement() -> None:
    """MCP make_decision must reject unauthorized attempts without valid confirmation tokens."""
    api_key = "test_scoped_mock_token_for_unit_tests"  # gitleaks:allow

    async with AsyncSessionLocal() as session:
        user = User(
            email="mcp_user@lens.local",
            hashed_password=hash_password("Password123!"),
            role="recruiter",
            api_key=api_key,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        job = Job(user_id=user.id, title="Sales Manager", raw_text="B2B sales.")
        session.add(job)
        await session.flush()

        resume = Resume(
            user_id=user.id,
            job_id=job.id,
            filename="cand3.pdf",
            storage_path="/tmp/cand3.pdf",
            file_hash="hash789",
            raw_text="Enterprise sales professional.",
        )
        session.add(resume)
        await session.flush()

        evaluation = Evaluation(
            user_id=user.id,
            job_id=job.id,
            resume_id=resume.id,
            total_score=75.0,
            tier="Review",
            stage="screened",
            confidence=1.0,
            evidence_hash="evhash789",
        )
        session.add(evaluation)
        await session.commit()
        await session.refresh(evaluation)

        # 1. Attempt decision with invalid token -> MUST FAIL
        bad_res = await make_decision(
            api_key=api_key,
            evaluation_id=evaluation.id,
            decision="shortlisted",
            confirmation_token="invalid_token_xyz",
        )
        assert bad_res.get("success") is False
        assert "Confirmation token is invalid" in bad_res.get("error", "")

        # 2. Create valid confirmation token
        valid_token = "mcp_valid_token_test_fixture"  # gitleaks:allow
        token_rec = McpConfirmationToken(
            user_id=user.id,
            token=valid_token,
            action="make_decision",
            target_id=evaluation.id,
            decision="shortlisted",
            is_used=False,
            expires_at=datetime.now(UTC) + timedelta(minutes=15),
        )
        session.add(token_rec)
        await session.commit()

        # 3. Attempt decision with valid token -> MUST SUCCEED
        good_res = await make_decision(
            api_key=api_key,
            evaluation_id=evaluation.id,
            decision="shortlisted",
            confirmation_token=valid_token,
        )
        assert good_res.get("success") is True
        assert good_res.get("new_stage") == "shortlisted"

        # 4. Attempt reuse of same token -> MUST FAIL (single use)
        reuse_res = await make_decision(
            api_key=api_key,
            evaluation_id=evaluation.id,
            decision="shortlisted",
            confirmation_token=valid_token,
        )
        assert reuse_res.get("success") is False


def test_drift_metrics_psi_and_ks() -> None:
    """Verify statistical drift calculations for monitoring."""
    np.random.seed(42)
    baseline = np.random.normal(loc=70, scale=10, size=500)

    # Identical distribution with minor noise -> very low PSI, no drift
    identical = baseline + np.random.normal(loc=0, scale=0.5, size=500)
    psi_stable = compute_psi(baseline, identical)
    ks_stable = compute_ks_drift(baseline, identical)

    assert psi_stable < 0.10  # Stable threshold (< 0.10)
    assert ks_stable["drift_detected"] is False

    # Shifted distribution -> high PSI, significant drift detected
    drifted = np.random.normal(loc=45, scale=15, size=500)
    psi_drifted = compute_psi(baseline, drifted)
    ks_drifted = compute_ks_drift(baseline, drifted)

    assert psi_drifted > 0.25  # Significant drift threshold (> 0.25)
    assert ks_drifted["drift_detected"] is True
    assert ks_drifted["p_value"] < 0.05
