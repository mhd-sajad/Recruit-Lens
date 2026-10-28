"""
Tests for 5 critical security controls:
1. auth expiry
2. role downgrade
3. audit immutability
4. quota enforcement
5. webhook signature
"""

import hashlib
import hmac
from datetime import timedelta
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from app.auth.security import create_access_token, hash_password, verify_webhook_signature
from app.config import settings
from app.db.models import AuditLog, User
from app.db.session import AsyncSessionLocal, init_db
from app.main import app


@pytest.mark.asyncio
async def test_auth_expiry() -> None:
    """1. Auth expiry: Expired JWT tokens must return 401 Unauthorized."""
    await init_db()

    async with AsyncSessionLocal() as db:
        user = User(
            email="expired_user@recruitlens.local",
            hashed_password=hash_password("ValidPassword123!"),
            full_name="Expired User",
            role="recruiter",
        )
        db.add(user)
        await db.commit()
        user_id = user.id

    # Create expired token (-5 minutes)
    expired_token = create_access_token(
        {"sub": user_id, "role": "recruiter"},
        expires_delta=timedelta(minutes=-5),
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {expired_token}"},
        )
        assert resp.status_code == 401
        assert "expired" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_role_downgrade() -> None:
    """2. Role downgrade: Viewer role must be forbidden from creating jobs or modifying requisitions."""
    await init_db()

    async with AsyncSessionLocal() as db:
        user = User(
            email="viewer_user@recruitlens.local",
            hashed_password=hash_password("ValidPassword123!"),
            full_name="Viewer User",
            role="viewer",  # downgraded from recruiter/admin
        )
        db.add(user)
        await db.commit()
        user_id = user.id

    valid_token = create_access_token({"sub": user_id, "role": "viewer"})

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Attempt to create a job (requires recruiter or admin)
        resp = await client.post(
            "/api/v1/jobs/",
            headers={"Authorization": f"Bearer {valid_token}"},
            json={
                "title": "Software Engineer",
                "raw_text": "Python experience required. 3 years.",
            },
        )
        assert resp.status_code == 403
        assert "requires one of the following roles" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_audit_immutability() -> None:
    """3. Audit immutability: Audit logs are append-only. Modification and deletion endpoints must not exist (405)."""
    await init_db()

    async with AsyncSessionLocal() as db:
        user = User(
            email="audit_user@recruitlens.local",
            hashed_password=hash_password("ValidPassword123!"),
            full_name="Audit User",
            role="admin",
        )
        db.add(user)
        await db.commit()
        user_id = user.id

        log_entry = AuditLog(
            user_id=user_id,
            action="candidate_decision",
            target_type="candidate",
            target_id="cand_123",
            details_json={"decision": "SHORTLIST"},
        )
        db.add(log_entry)
        await db.commit()
        log_id = log_entry.id

    token = create_access_token({"sub": user_id, "role": "admin"})

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # GET is allowed
        resp_get = await client.get(
            "/api/v1/audit-logs/",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp_get.status_code == 200
        logs = resp_get.json()
        assert any(log_item["id"] == log_id for log_item in logs)

        # POST / PUT / DELETE on audit logs must be rejected (404/405), proving audit trail is immutable
        resp_post = await client.post(
            "/api/v1/audit-logs/",
            headers={"Authorization": f"Bearer {token}"},
            json={"action": "tampered_action"},
        )
        assert resp_post.status_code == 405

        resp_put = await client.put(
            f"/api/v1/audit-logs/{log_id}",
            headers={"Authorization": f"Bearer {token}"},
            json={"details": {"tampered": True}},
        )
        assert resp_put.status_code in (404, 405)

        resp_del = await client.delete(
            f"/api/v1/audit-logs/{log_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp_del.status_code in (404, 405)


@pytest.mark.asyncio
async def test_quota_enforcement() -> None:
    """4. Quota enforcement: Batch uploads exceeding the MAX_BATCH_RESUMES cap must be rejected."""
    await init_db()

    async with AsyncSessionLocal() as db:
        user = User(
            email="quota_user@recruitlens.local",
            hashed_password=hash_password("ValidPassword123!"),
            full_name="Quota User",
            role="recruiter",
        )
        db.add(user)
        await db.commit()
        user_id = user.id

    token = create_access_token({"sub": user_id, "role": "recruiter"})

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Create a job first
        job_res = await client.post(
            "/api/v1/jobs/",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "title": "Backend Developer",
                "raw_text": "Need python developer with sql experience.",
            },
        )
        assert job_res.status_code == 201
        job_id = job_res.json()["id"]

        # Exceed MAX_BATCH_RESUMES (which is 200)
        files = [
            ("files", (f"resume_{i}.pdf", b"%PDF-1.4 test resume content", "application/pdf"))
            for i in range(settings.MAX_BATCH_RESUMES + 5)
        ]
        resp = await client.post(
            f"/api/v1/resumes/upload/{job_id}",
            headers={"Authorization": f"Bearer {token}"},
            files=files,
        )
        assert resp.status_code in (400, 413)
        assert (
            "exceeds" in resp.json()["detail"].lower() or "limit" in resp.json()["detail"].lower()
        )


def test_webhook_signature() -> None:
    """5. Webhook signature: Valid HMAC-SHA256 signatures must pass; tampered payloads must fail."""
    secret = "test-webhook-secret-key-12345"
    payload = b'{"event":"candidate.shortlisted","candidate_id":"cand_999"}'
    valid_sig = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()

    # Valid signature
    assert verify_webhook_signature(payload, valid_sig, secret) is True
    # Valid with sha256= prefix
    assert verify_webhook_signature(payload, f"sha256={valid_sig}", secret) is True

    # Tampered payload
    tampered_payload = b'{"event":"candidate.shortlisted","candidate_id":"cand_999_tampered"}'
    assert verify_webhook_signature(tampered_payload, valid_sig, secret) is False

    # Invalid secret
    assert verify_webhook_signature(payload, valid_sig, "wrong-secret") is False

    # Forged signature
    assert verify_webhook_signature(payload, "invalid_sig_abc123", secret) is False


@pytest.mark.asyncio
async def test_evidence_packet_and_emailer_coverage() -> None:
    """Verify evidence packet compilation and email drafting with deterministic fallback."""
    from app.core.features import extract_candidate_features
    from app.core.jd_requirements import JobRequirements
    from app.core.models import ContactPII, ResumeChunk, ResumeParseResult
    from app.core.tiers import TierAssignmentResult
    from app.llm.agents.emailer import generate_candidate_emails
    from app.llm.evidence import compile_evidence_packet
    from app.llm.provider import NoLLMProvider

    parsed = ResumeParseResult(
        resume_id="cand_cov_01",
        is_resume=True,
        gate_confidence=0.95,
        gate_signals={"has_experience": True},
        parse_confidence=0.9,
        page_count=1,
        layout_type="single_column",
        pii=ContactPII(name="Alice Smith", email="alice@test.com", phone="123-456-7890"),
        scoring_text="Python and AWS developer",
        raw_text="Alice Smith is an experienced Python and AWS engineer.",
        sections={"summary": "Experienced engineer"},
        experiences=[],
        educations=[],
        skills=["python", "aws"],
    )
    chunks = [
        ResumeChunk(
            resume_id="cand_cov_01",
            chunk_id="c_01",
            section="EXP",
            text="Alice Smith worked 4 years in Python and AWS.",
            metadata={"token_count": 10},
        )
    ]
    jd_reqs = JobRequirements(
        job_id="jd_01",
        title="Python Engineer",
        must_have_skills=["python"],
        nice_to_have_skills=["aws"],
        min_years_experience=3.0,
        min_education_rank=2,
    )
    feats = extract_candidate_features(parsed, jd_reqs)
    tier_res = TierAssignmentResult(
        resume_id="cand_cov_01",
        tier="Interview",
        final_score=0.85,
        tier_rank=2,
        recommended_action="Proceed to technical interview",
    )

    # 1. Evidence compilation
    packet = compile_evidence_packet(parsed, chunks, feats, tier_res, jd_reqs, top_k=2)
    assert packet.candidate_id == "cand_cov_01"
    assert len(packet.retrieved_chunks) == 1
    assert "Alice Smith" not in packet.retrieved_chunks[0].text  # Redacted PII

    # 2. Email drafting with NoLLMProvider fallback
    provider = NoLLMProvider()
    emails, is_fb, _, _ = await generate_candidate_emails(packet, provider)
    assert is_fb is True
    assert "interview" in emails.invite.subject.lower()
    assert "application" in emails.hold.subject.lower()
    assert "application" in emails.rejection.subject.lower()


@pytest.mark.asyncio
async def test_local_storage_backend_lifecycle(tmp_path: Path) -> None:
    """Verify local file storage abstraction operations and path traversal security."""
    from app.core.storage import LocalStorageBackend

    storage = LocalStorageBackend(base_dir=tmp_path)
    key = "test_doc.pdf"
    content = b"%PDF-1.4 test document"

    # Save
    saved_key = await storage.save_file(key, content)
    assert saved_key == key

    # Get
    retrieved = await storage.get_file(key)
    assert retrieved == content

    # Signed URL
    url = await storage.get_signed_url(key, expires_in_seconds=600)
    assert "exp=" in url
    assert "sig=" in url

    # Traversal attack
    with pytest.raises(ValueError, match="Path traversal detected"):
        storage._resolve_path("../../etc/passwd")

    # Delete
    deleted = await storage.delete_file(key)
    assert deleted is True
    # Non-existent get
    with pytest.raises(FileNotFoundError):
        await storage.get_file(key)
