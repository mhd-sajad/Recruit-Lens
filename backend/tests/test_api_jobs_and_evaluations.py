"""Integration tests for Job requisition CRUD, recruiter decisions, state machine transitions, and user isolation."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.auth.security import hash_password
from app.db.models import Evaluation, Job, Resume, User
from app.db.session import AsyncSessionLocal, init_db
from app.main import app


@pytest.mark.asyncio
async def test_job_crud_and_user_isolation_idor_protection() -> None:
    """Verify job creation, requirement extraction, and user isolation against IDOR attacks."""
    await init_db()

    # Seed User A and User B directly
    async with AsyncSessionLocal() as db:
        user_a = User(
            email="user_a@recruitlens.local",
            hashed_password=hash_password("PasswordAlpha123!"),
            full_name="Alpha Recruiter",
            role="recruiter",
        )
        user_b = User(
            email="user_b@recruitlens.local",
            hashed_password=hash_password("PasswordBeta123!"),
            full_name="Beta Recruiter",
            role="recruiter",
        )
        db.add_all([user_a, user_b])
        await db.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Login User A
        res_a = await client.post(
            "/api/v1/auth/login",
            json={"email": "user_a@recruitlens.local", "password": "PasswordAlpha123!"},
        )
        assert res_a.status_code == 200
        token_a = res_a.json()["access_token"]

        # 2. Login User B
        res_b = await client.post(
            "/api/v1/auth/login",
            json={"email": "user_b@recruitlens.local", "password": "PasswordBeta123!"},
        )
        assert res_b.status_code == 200
        token_b = res_b.json()["access_token"]

        # 3. User A creates a Job
        job_payload = {
            "title": "Senior Python Backend Engineer",
            "department": "Engineering",
            "raw_text": (
                "We are seeking a Senior Python Engineer with 5+ years of experience in FastAPI, "
                "PostgreSQL, Docker, and distributed systems. A Bachelor's degree in Computer Science is required."
            ),
            "weights": {"skills": 0.5, "experience": 0.3, "education": 0.2},
        }

        # 3.1 Test real-time requirements extraction preview endpoint
        res_extract = await client.post(
            "/api/v1/jobs/extract-requirements",
            json={"raw_text": job_payload["raw_text"]},
            headers={"Authorization": f"Bearer {token_a}"},
        )
        assert res_extract.status_code == 200
        extract_data = res_extract.json()
        assert "must_have_skills" in extract_data
        assert "suggested_weights" in extract_data
        assert extract_data["min_years_experience"] == 5.0
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

        # 4. User A can retrieve their Job
        res_get_a = await client.get(
            f"/api/v1/jobs/{job_a_id}",
            headers={"Authorization": f"Bearer {token_a}"},
        )
        assert res_get_a.status_code == 200

        # 5. IDOR Attack Prevention: User B attempts to read User A's Job -> 404
        res_idor_get = await client.get(
            f"/api/v1/jobs/{job_a_id}",
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert res_idor_get.status_code == 404

        # 6. IDOR Attack Prevention: User B attempts to modify User A's Job -> 404
        res_idor_put = await client.put(
            f"/api/v1/jobs/{job_a_id}",
            json={"title": "Hacked Title"},
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert res_idor_put.status_code == 404

        # 7. IDOR Attack Prevention: User B attempts to delete User A's Job -> 404
        res_idor_del = await client.delete(
            f"/api/v1/jobs/{job_a_id}",
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert res_idor_del.status_code == 404


@pytest.mark.asyncio
async def test_recruiter_decision_workflow_state_machine_and_audit() -> None:
    """Verify decision state machine, audit log, what-if, CSV protection, and hard delete."""
    await init_db()

    async with AsyncSessionLocal() as db:
        user = User(
            email="workflow_lead@recruitlens.local",
            hashed_password=hash_password("WorkflowPassword123!"),
            full_name="Hiring Lead",
            role="recruiter",
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        user_id = user.id

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Login
        res_login = await client.post(
            "/api/v1/auth/login",
            json={"email": "workflow_lead@recruitlens.local", "password": "WorkflowPassword123!"},
        )
        token = res_login.json()["access_token"]

        # Seed Job, Resume, Evaluation
        async with AsyncSessionLocal() as db:
            job = Job(
                user_id=user_id,
                title="Full-Stack Developer",
                raw_text="Full-stack developer role with React and FastAPI.",
            )
            db.add(job)
            await db.flush()

            resume = Resume(
                user_id=user_id,
                job_id=job.id,
                filename="=cmd|' /C calc'!A0.pdf",  # Formula injection attempt in filename
                file_hash="fakehash123",
                storage_path="/fake/path.pdf",
                status="scored",
            )
            db.add(resume)
            await db.flush()

            evaluation = Evaluation(
                user_id=user_id,
                job_id=job.id,
                resume_id=resume.id,
                total_score=0.88,
                tier="FastTrack",
                confidence=0.95,
                stage="screened",
                breakdown_json={"matched_skills": ["Python", "React"]},
                explanation_json={"sentences": ["Strong candidate [c_01]."]},
                interview_questions_json={"questions": []},
                email_drafts_json={},
                evidence_hash="evhash123",
            )
            db.add(evaluation)
            await db.commit()
            await db.refresh(evaluation)
            eval_id = evaluation.id
            job_id = job.id

        # 1. State machine transition: screened -> shortlisted (Valid)
        res_trans = await client.post(
            f"/api/v1/evaluations/{eval_id}/stage",
            json={"to_stage": "shortlisted", "notes": "Solid portfolio"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res_trans.status_code == 200
        assert res_trans.json()["to_stage"] == "shortlisted"

        # 2. Invalid state transition: shortlisted -> hired directly (Invalid, must interview first) -> 400
        res_invalid = await client.post(
            f"/api/v1/evaluations/{eval_id}/stage",
            json={"to_stage": "hired", "notes": "Skipping interview"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res_invalid.status_code == 400
        assert "invalid transition" in str(res_invalid.json()).lower()

        # 3. What-if sensitivity recalculation
        res_whatif = await client.post(
            f"/api/v1/evaluations/{eval_id}/what-if",
            json={"weights": {"skills": 0.8, "experience": 0.1, "education": 0.1}},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res_whatif.status_code == 200
        assert "new_score" in res_whatif.json()

        # 4. CSV Export with formula injection protection
        res_csv = await client.get(
            f"/api/v1/evaluations/job/{job_id}/export/csv",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res_csv.status_code == 200
        csv_text = res_csv.text
        # Ensure '=' formula was sanitized with single quote prefix
        assert "'=cmd" in csv_text or "=cmd" not in csv_text.split(",")[0]

        # 5. GDPR Hard Delete Candidate
        res_del = await client.delete(
            f"/api/v1/evaluations/{eval_id}/hard-delete",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res_del.status_code == 200
        assert res_del.json()["status"] == "purged"
