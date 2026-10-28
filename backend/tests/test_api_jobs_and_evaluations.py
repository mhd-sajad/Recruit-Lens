"""Integration tests for Job requisition CRUD, recruiter decisions, and multi-tenant isolation."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.db.models import Evaluation, Job, Resume
from app.db.session import AsyncSessionLocal, init_db
from app.main import app


@pytest.mark.asyncio
async def test_job_crud_and_multitenant_idor_protection() -> None:
    """Verify job creation, requirement extraction, and multi-tenant isolation against IDOR attacks."""
    await init_db()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Register Tenant A
        reg_a = await client.post(
            "/api/v1/auth/register",
            json={
                "tenant_name": "Tenant Alpha",
                "tenant_slug": "tenant-alpha",
                "email": "recruiter@alpha.local",
                "password": "PasswordAlpha123!",
                "full_name": "Alpha Recruiter",
            },
        )
        assert reg_a.status_code == 201
        token_a = reg_a.json()["access_token"]

        # 2. Register Tenant B
        reg_b = await client.post(
            "/api/v1/auth/register",
            json={
                "tenant_name": "Tenant Beta",
                "tenant_slug": "tenant-beta",
                "email": "recruiter@beta.local",
                "password": "PasswordBeta123!",
                "full_name": "Beta Recruiter",
            },
        )
        assert reg_b.status_code == 201
        token_b = reg_b.json()["access_token"]

        # 3. Tenant A creates a Job
        job_payload = {
            "title": "Senior Python Backend Engineer",
            "department": "Engineering",
            "raw_text": (
                "We are seeking a Senior Python Engineer with 5+ years of experience in FastAPI, "
                "PostgreSQL, Docker, and distributed systems. A Bachelor's degree in Computer Science is required."
            ),
            "weights": {"skills": 0.5, "experience": 0.3, "education": 0.2},
        }
        res_create = await client.post(
            "/api/v1/jobs/",
            json=job_payload,
            headers={"Authorization": f"Bearer {token_a}"},
        )
        assert res_create.status_code == 201
        job_a_data = res_create.json()
        job_a_id = job_a_data["id"]
        assert job_a_data["title"] == "Senior Python Backend Engineer"
        assert "requirements_json" in job_a_data
        assert len(job_a_data["requirements_json"]["must_have_skills"]) > 0

        # 4. Tenant A can retrieve their Job
        res_get_a = await client.get(
            f"/api/v1/jobs/{job_a_id}",
            headers={"Authorization": f"Bearer {token_a}"},
        )
        assert res_get_a.status_code == 200

        # 5. IDOR Attack Prevention: Tenant B attempts to read Tenant A's Job -> 404
        res_idor_get = await client.get(
            f"/api/v1/jobs/{job_a_id}",
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert res_idor_get.status_code == 404

        # 6. IDOR Attack Prevention: Tenant B attempts to modify Tenant A's Job -> 404
        res_idor_put = await client.put(
            f"/api/v1/jobs/{job_a_id}",
            json={"title": "Hacked Title"},
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert res_idor_put.status_code == 404

        # 7. IDOR Attack Prevention: Tenant B attempts to delete Tenant A's Job -> 404
        res_idor_del = await client.delete(
            f"/api/v1/jobs/{job_a_id}",
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert res_idor_del.status_code == 404


@pytest.mark.asyncio
async def test_recruiter_decision_workflow_and_audit_log() -> None:
    """Verify candidate decision actions (shortlist, reject) generate immutable audit logs."""
    await init_db()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Register recruiter
        reg = await client.post(
            "/api/v1/auth/register",
            json={
                "tenant_name": "Workflow Corp",
                "tenant_slug": "workflow-corp",
                "email": "lead@workflow.local",
                "password": "WorkflowPassword123!",
                "full_name": "Hiring Lead",
            },
        )
        assert reg.status_code == 201
        token = reg.json()["access_token"]

        # Get me to know tenant_id
        me_res = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        tenant_id = me_res.json()["tenant_id"]

        # 2. Seed a Job, Resume, and Evaluation directly in DB
        async with AsyncSessionLocal() as db:
            job = Job(
                tenant_id=tenant_id,
                title="Full-Stack Developer",
                raw_text="Full-stack developer role with React and FastAPI.",
            )
            db.add(job)
            await db.flush()

            resume = Resume(
                tenant_id=tenant_id,
                job_id=job.id,
                filename="candidate_smith.pdf",
                file_hash="fakehash123",
                file_path="/fake/path.pdf",
                status="scored",
            )
            db.add(resume)
            await db.flush()

            evaluation = Evaluation(
                tenant_id=tenant_id,
                job_id=job.id,
                resume_id=resume.id,
                total_score=0.88,
                tier="Strong Fit",
                confidence=0.95,
                breakdown_json={"matched_skills": ["Python", "React"]},
                explanation_json={"sentences": ["Strong candidate."]},
                questions_json={"questions": []},
                email_drafts_json={},
                decision="pending",
                evidence_hash="evhash123",
            )
            db.add(evaluation)
            await db.commit()
            await db.refresh(evaluation)
            eval_id = evaluation.id

        # 3. Retrieve evaluation details
        res_detail = await client.get(
            f"/api/v1/evaluations/{eval_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res_detail.status_code == 200
        detail_data = res_detail.json()
        assert detail_data["total_score"] == 0.88
        assert detail_data["tier"] == "Strong Fit"
        assert detail_data["decision"] == "pending"

        # 4. Recruiter records decision: Shortlisted
        dec_payload = {
            "decision": "shortlisted",
            "decision_notes": "Impressive background in distributed systems and FastAPI.",
        }
        res_dec = await client.post(
            f"/api/v1/evaluations/{eval_id}/decision",
            json=dec_payload,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res_dec.status_code == 200
        dec_data = res_dec.json()
        assert dec_data["decision"] == "shortlisted"
        assert "audit_log_id" in dec_data
        audit_id = dec_data["audit_log_id"]

        # 5. Check audit logs endpoint
        res_logs = await client.get(
            "/api/v1/audit-logs/",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res_logs.status_code == 200
        logs_data = res_logs.json()
        assert len(logs_data) >= 1
        found_log = next((item for item in logs_data if item["id"] == audit_id), None)
        assert found_log is not None
        assert found_log["action"] == "candidate_decision"
        assert found_log["details"]["new_decision"] == "shortlisted"
        assert found_log["details"]["candidate_score"] == 0.88
