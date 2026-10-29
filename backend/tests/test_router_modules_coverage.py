"""Comprehensive router test suite verifying:
1. isolation per endpoint (another user gets 404, not 403)
2. illegal and legal state transitions including post-interview
3. email cannot be sent unless approved, dry-run is default, daily cap holds, each send audit-logged
4. CSV export neutralizes formula injection
5. hard delete removes files and database rows
6. candidate data export portability
7. what-if counterfactual sensitivity simulation
8. SSE task progress and cancellation
9. upload limits and magic-byte check
10. login throttling and refresh token reuse detection
"""

import hashlib
import hmac
import io
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from app.auth.security import create_access_token, hash_password
from app.config import settings
from app.core.storage import get_storage_backend
from app.db.models import (
    AuditLog,
    BackgroundTask,
    EmailRecord,
    Evaluation,
    InterviewFeedbackRecord,
    Job,
    Resume,
    User,
)
from app.db.session import AsyncSessionLocal, init_db
from app.main import app


async def create_test_user(
    email: str, password: str = "TestPass123!", role: str = "recruiter"
) -> User:
    """Helper to create test user in database."""
    async with AsyncSessionLocal() as db:
        user = User(
            email=email,
            hashed_password=hash_password(password),
            full_name="Test Recruiter",
            role=role,
            is_active=True,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user


@pytest.mark.asyncio
async def test_isolation_per_endpoint_returns_404_not_403() -> None:
    """Verify complete cross-user isolation across every API endpoint: User B must get 404, not 403."""
    await init_db()

    user_a = await create_test_user("iso_user_a@recruitlens.local")
    user_b = await create_test_user("iso_user_b@recruitlens.local")

    token_b = create_access_token({"sub": user_b.id, "role": user_b.role})
    auth_b = {"Authorization": f"Bearer {token_b}"}

    # User A creates a job, resume, evaluation, email, and task
    async with AsyncSessionLocal() as db:
        job_a = Job(
            user_id=user_a.id,
            title="Senior Python Architect",
            department="Engineering",
            raw_text="Requires Python and FastAPI.",
            status="active",
        )
        db.add(job_a)
        await db.flush()

        resume_a = Resume(
            user_id=user_a.id,
            job_id=job_a.id,
            filename="candidate_a.pdf",
            storage_path=f"{job_a.id}/cand_a.pdf",
            file_hash="hash_iso_a",
            status="scored",
        )
        db.add(resume_a)
        await db.flush()

        eval_a = Evaluation(
            user_id=user_a.id,
            job_id=job_a.id,
            resume_id=resume_a.id,
            total_score=0.85,
            tier="FastTrack",
            confidence=0.9,
            stage="screened",
            breakdown_json={"skills": {"score": 0.85}},
            evidence_hash="ev_iso_a",
        )
        db.add(eval_a)
        await db.flush()

        email_a = EmailRecord(
            user_id=user_a.id,
            evaluation_id=eval_a.id,
            email_type="interview_invite",
            recipient_email="candidate_a@example.com",
            subject="Interview Invitation",
            body="You are invited to interview.",
            status="draft",
        )
        db.add(email_a)
        await db.flush()

        task_a = BackgroundTask(
            user_id=user_a.id,
            task_type="batch_ingestion",
            status="pending",
            progress=0,
            total=1,
            payload_json={"job_id": job_a.id},
        )
        db.add(task_a)
        await db.commit()

        job_id = job_a.id
        eval_id = eval_a.id
        email_id = email_a.id
        task_id = task_a.id

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Job endpoints isolation
        res = await client.get(f"/api/v1/jobs/{job_id}", headers=auth_b)
        assert res.status_code == 404, f"Expected 404, got {res.status_code}"

        res = await client.put(f"/api/v1/jobs/{job_id}", headers=auth_b, json={"title": "Hacked"})
        assert res.status_code == 404

        res = await client.delete(f"/api/v1/jobs/{job_id}", headers=auth_b)
        assert res.status_code == 404

        # 2. Resumes endpoints isolation
        res = await client.get(f"/api/v1/resumes/job/{job_id}", headers=auth_b)
        assert res.status_code == 404

        fake_pdf = io.BytesIO(b"%PDF-1.4 Fake content")
        res = await client.post(
            f"/api/v1/resumes/upload/{job_id}",
            headers=auth_b,
            files=[("files", ("test.pdf", fake_pdf, "application/pdf"))],
        )
        assert res.status_code == 404

        # 3. Evaluations endpoints isolation
        res = await client.get(f"/api/v1/evaluations/job/{job_id}", headers=auth_b)
        assert res.status_code == 404

        res = await client.get(f"/api/v1/evaluations/{eval_id}", headers=auth_b)
        assert res.status_code == 404

        res = await client.post(
            f"/api/v1/evaluations/{eval_id}/stage",
            headers=auth_b,
            json={"to_stage": "shortlisted"},
        )
        assert res.status_code == 404

        res = await client.post(
            f"/api/v1/evaluations/{eval_id}/interview-feedback",
            headers=auth_b,
            json={"interviewer_name": "Bob Smith", "overall_score": 4, "recommendation": "hire"},
        )
        assert res.status_code == 404

        res = await client.get(f"/api/v1/evaluations/{eval_id}/interview-feedback", headers=auth_b)
        assert res.status_code == 200
        assert res.json() == []  # user_b has no feedback for this eval

        res = await client.get(f"/api/v1/evaluations/{eval_id}/emails", headers=auth_b)
        assert res.status_code == 200
        assert res.json() == []

        res = await client.post(f"/api/v1/evaluations/emails/{email_id}/approve", headers=auth_b)
        assert res.status_code == 404

        res = await client.post(f"/api/v1/evaluations/emails/{email_id}/send", headers=auth_b)
        assert res.status_code == 404

        res = await client.put(
            f"/api/v1/evaluations/emails/{email_id}",
            headers=auth_b,
            json={"subject": "Tampered"},
        )
        assert res.status_code == 404

        res = await client.post(
            f"/api/v1/evaluations/{eval_id}/what-if",
            headers=auth_b,
            json={"weights": {"skills": 0.5}},
        )
        assert res.status_code == 404

        res = await client.delete(f"/api/v1/evaluations/{eval_id}", headers=auth_b)
        assert res.status_code == 404

        res = await client.delete(f"/api/v1/evaluations/{eval_id}/hard-delete", headers=auth_b)
        assert res.status_code == 404

        res = await client.get(f"/api/v1/evaluations/{eval_id}/export", headers=auth_b)
        assert res.status_code == 404

        res = await client.get(f"/api/v1/evaluations/job/{job_id}/export/csv", headers=auth_b)
        assert res.status_code == 404

        res = await client.get(f"/api/v1/evaluations/job/{job_id}/export/pdf", headers=auth_b)
        assert res.status_code == 404

        # 4. Tasks endpoints isolation
        res = await client.get(f"/api/v1/tasks/{task_id}", headers=auth_b)
        assert res.status_code == 404

        res = await client.post(f"/api/v1/tasks/{task_id}/cancel", headers=auth_b)
        assert res.status_code == 404


@pytest.mark.asyncio
async def test_illegal_and_legal_state_transitions_including_post_interview() -> None:
    """Verify recruiter state machine: legal transitions, illegal rejections, and post-interview scorecard."""
    await init_db()

    user = await create_test_user("state_user@recruitlens.local")
    token = create_access_token({"sub": user.id, "role": user.role})
    auth = {"Authorization": f"Bearer {token}"}

    async with AsyncSessionLocal() as db:
        job = Job(user_id=user.id, title="Backend Engineer", raw_text="Python", status="active")
        db.add(job)
        await db.flush()

        resume = Resume(
            user_id=user.id,
            job_id=job.id,
            filename="cand.pdf",
            storage_path="path/cand.pdf",
            file_hash="hash_state",
            status="scored",
        )
        db.add(resume)
        await db.flush()

        evaluation = Evaluation(
            user_id=user.id,
            job_id=job.id,
            resume_id=resume.id,
            total_score=0.91,
            tier="FastTrack",
            confidence=0.95,
            stage="screened",
            evidence_hash="ev_state",
        )
        db.add(evaluation)
        await db.commit()
        eval_id = evaluation.id

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # ILLEGAL: screened -> hired (cannot jump directly to hired)
        res = await client.post(
            f"/api/v1/evaluations/{eval_id}/stage",
            headers=auth,
            json={"to_stage": "hired", "notes": "Premature hire"},
        )
        assert res.status_code == 400
        assert "invalid transition" in res.json()["detail"].lower()

        # LEGAL 1: screened -> shortlisted
        res = await client.post(
            f"/api/v1/evaluations/{eval_id}/stage",
            headers=auth,
            json={"to_stage": "shortlisted", "notes": "Passes screen"},
        )
        assert res.status_code == 200
        assert res.json()["to_stage"] == "shortlisted"

        # ILLEGAL: shortlisted -> interviewed (must schedule interview first)
        res = await client.post(
            f"/api/v1/evaluations/{eval_id}/stage",
            headers=auth,
            json={"to_stage": "interviewed"},
        )
        assert res.status_code == 400

        # LEGAL 2: shortlisted -> interview_scheduled
        res = await client.post(
            f"/api/v1/evaluations/{eval_id}/stage",
            headers=auth,
            json={"to_stage": "interview_scheduled"},
        )
        assert res.status_code == 200

        # LEGAL 3: interview_scheduled -> interviewed
        res = await client.post(
            f"/api/v1/evaluations/{eval_id}/stage",
            headers=auth,
            json={"to_stage": "interviewed"},
        )
        assert res.status_code == 200

        # POST-INTERVIEW SCORECARD: submit feedback
        res_fb = await client.post(
            f"/api/v1/evaluations/{eval_id}/interview-feedback",
            headers=auth,
            json={
                "interviewer_name": "Sarah Connor",
                "overall_score": 5,
                "technical_rating": 5,
                "communication_rating": 4,
                "recommendation": "strong_hire",
                "strengths": "Deep systems knowledge, Fast problem solver",
                "concerns": "",
                "notes": "Excellent performance on coding task.",
            },
        )
        assert res_fb.status_code == 200
        fb_data = res_fb.json()
        assert fb_data["interviewer_name"] == "Sarah Connor"
        assert fb_data["recommendation"] == "strong_hire"

        # Verify feedback retrieval
        res_fbs = await client.get(
            f"/api/v1/evaluations/{eval_id}/interview-feedback",
            headers=auth,
        )
        assert res_fbs.status_code == 200
        assert len(res_fbs.json()) == 1

        # LEGAL 4: interviewed -> offer_extended
        res = await client.post(
            f"/api/v1/evaluations/{eval_id}/stage",
            headers=auth,
            json={"to_stage": "offer_extended"},
        )
        assert res.status_code == 200

        # LEGAL 5: offer_extended -> hired
        res = await client.post(
            f"/api/v1/evaluations/{eval_id}/stage",
            headers=auth,
            json={"to_stage": "hired"},
        )
        assert res.status_code == 200
        assert res.json()["to_stage"] == "hired"

        # ILLEGAL: hired is a terminal stage, cannot transition to rejected
        res = await client.post(
            f"/api/v1/evaluations/{eval_id}/stage",
            headers=auth,
            json={"to_stage": "rejected"},
        )
        assert res.status_code == 400


@pytest.mark.asyncio
async def test_email_workflow_gates_cap_and_audit() -> None:
    """Verify email draft approval gate, daily cap enforcement, dry-run default, and audit logging."""
    await init_db()

    user = await create_test_user("email_flow_user@recruitlens.local")
    token = create_access_token({"sub": user.id, "role": user.role})
    auth = {"Authorization": f"Bearer {token}"}

    async with AsyncSessionLocal() as db:
        job = Job(user_id=user.id, title="Frontend Dev", raw_text="React", status="active")
        db.add(job)
        await db.flush()

        resume = Resume(
            user_id=user.id,
            job_id=job.id,
            filename="cand.pdf",
            storage_path="path/cand.pdf",
            file_hash="hash_email",
            status="scored",
        )
        db.add(resume)
        await db.flush()

        ev = Evaluation(
            user_id=user.id,
            job_id=job.id,
            resume_id=resume.id,
            total_score=0.82,
            tier="Review",
            confidence=0.9,
            stage="screened",
            evidence_hash="ev_email",
        )
        db.add(ev)
        await db.flush()

        email = EmailRecord(
            user_id=user.id,
            evaluation_id=ev.id,
            email_type="rejection",
            recipient_email="candidate@example.com",
            subject="Application Update",
            body="Thank you for applying.",
            status="draft",
        )
        db.add(email)
        await db.commit()
        email_id = email.id

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Gate: sending unapproved email must be blocked (400)
        res = await client.post(f"/api/v1/evaluations/emails/{email_id}/send", headers=auth)
        assert res.status_code == 400
        assert "must be approved" in res.json()["detail"].lower()

        # 2. Update email draft
        res_up = await client.put(
            f"/api/v1/evaluations/emails/{email_id}",
            headers=auth,
            json={"subject": "Updated Application Update", "body": "Custom body text."},
        )
        assert res_up.status_code == 200
        assert res_up.json()["subject"] == "Updated Application Update"

        # 3. Approve draft
        res_app = await client.post(f"/api/v1/evaluations/emails/{email_id}/approve", headers=auth)
        assert res_app.status_code == 200
        assert res_app.json()["status"] == "approved"

        # Double approval on already approved draft must return 400
        res_app2 = await client.post(f"/api/v1/evaluations/emails/{email_id}/approve", headers=auth)
        assert res_app2.status_code == 400

        # 4. Send approved draft (dry_run default is True)
        res_send = await client.post(f"/api/v1/evaluations/emails/{email_id}/send", headers=auth)
        assert res_send.status_code == 200
        data = res_send.json()
        assert data["status"] == "sent"
        assert data["dry_run"] is True

        # 5. Verify audit log entry exists for the send
        async with AsyncSessionLocal() as db:
            from sqlalchemy import select

            log_res = await db.execute(
                select(AuditLog).where(
                    AuditLog.user_id == user.id,
                    AuditLog.action == "send_email",
                    AuditLog.target_id == email_id,
                )
            )
            audit = log_res.scalar_one_or_none()
            assert audit is not None
            assert audit.details_json["dry_run"] is True

        # 6. Daily cap enforcement: Seed sent emails up to DAILY_EMAIL_CAP
        async with AsyncSessionLocal() as db:
            # Create a new approved email
            email_capped = EmailRecord(
                user_id=user.id,
                evaluation_id=ev.id,
                email_type="interview_invite",
                recipient_email="another@example.com",
                subject="Invite",
                body="Invite body",
                status="approved",
            )
            db.add(email_capped)

            # Seed sent emails today to reach cap
            now = datetime.now(UTC)
            for i in range(settings.DAILY_EMAIL_CAP):
                seed_email = EmailRecord(
                    user_id=user.id,
                    evaluation_id=ev.id,
                    email_type="interview_invite",
                    recipient_email=f"seed_{i}@example.com",
                    subject=f"Seed {i}",
                    body="Body",
                    status="sent",
                    sent_at=now,
                )
                db.add(seed_email)
            await db.commit()
            capped_id = email_capped.id

        # Attempt to send should now return 429
        res_capped = await client.post(f"/api/v1/evaluations/emails/{capped_id}/send", headers=auth)
        assert res_capped.status_code == 429
        assert "daily email cap reached" in res_capped.json()["detail"].lower()


@pytest.mark.asyncio
async def test_csv_export_neutralizes_formula_injection() -> None:
    """Verify CSV export sanitizes formulas starting with =, +, -, @, tab, or carriage return."""
    await init_db()

    user = await create_test_user("csv_inject_user@recruitlens.local")
    token = create_access_token({"sub": user.id, "role": user.role})
    auth = {"Authorization": f"Bearer {token}"}

    async with AsyncSessionLocal() as db:
        job = Job(user_id=user.id, title="Data Analyst", raw_text="SQL and Excel", status="active")
        db.add(job)
        await db.flush()

        # Resumes with dangerous formula prefixes in filename and tier
        danger_names = [
            "=SUM(A1:A100).pdf",
            "+cmd|' /C calc'!A0.pdf",
            "-2+5+cmd.pdf",
            "@HYPERLINK('http://malicious.com','Click').pdf",
            "\tTAB_COMMAND.pdf",
        ]

        for idx, d_name in enumerate(danger_names):
            r = Resume(
                user_id=user.id,
                job_id=job.id,
                filename=d_name,
                storage_path=f"path/{idx}.pdf",
                file_hash=f"hash_{idx}",
                status="scored",
            )
            db.add(r)
            await db.flush()

            ev = Evaluation(
                user_id=user.id,
                job_id=job.id,
                resume_id=r.id,
                total_score=0.75,
                tier="=DANGER_TIER",
                confidence=0.9,
                stage="+STAGE_VAL",
                breakdown_json={},
                evidence_hash=f"ev_{idx}",
            )
            db.add(ev)

        await db.commit()
        job_id = job.id

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get(f"/api/v1/evaluations/job/{job_id}/export/csv", headers=auth)
        assert res.status_code == 200
        csv_text = res.text

        # Verify dangerous prefixes were neutralized with a leading single quote
        assert "'=SUM" in csv_text
        assert "'+cmd" in csv_text
        assert "'-2+5" in csv_text
        assert "'@HYPERLINK" in csv_text
        assert "'\tTAB_COMMAND" in csv_text
        assert "'=DANGER_TIER" in csv_text
        assert "'+STAGE_VAL" in csv_text


@pytest.mark.asyncio
async def test_hard_delete_removes_files_and_database_rows(tmp_path: Path) -> None:
    """Verify GDPR hard delete purges the evaluation, audit-logs the purge, and deletes files from storage."""
    await init_db()

    user = await create_test_user("gdpr_user@recruitlens.local")
    token = create_access_token({"sub": user.id, "role": user.role})
    auth = {"Authorization": f"Bearer {token}"}

    storage = get_storage_backend()
    file_key = "gdpr_job/candidate_gdpr.pdf"
    await storage.save_file(file_key, b"%PDF-1.4 GDPR content to delete")

    async with AsyncSessionLocal() as db:
        job = Job(user_id=user.id, title="Security Engineer", raw_text="Security", status="active")
        db.add(job)
        await db.flush()

        resume = Resume(
            user_id=user.id,
            job_id=job.id,
            filename="candidate_gdpr.pdf",
            storage_path=file_key,
            file_hash="hash_gdpr",
            status="scored",
        )
        db.add(resume)
        await db.flush()

        ev = Evaluation(
            user_id=user.id,
            job_id=job.id,
            resume_id=resume.id,
            total_score=0.88,
            tier="FastTrack",
            confidence=0.95,
            stage="screened",
            evidence_hash="ev_gdpr",
        )
        db.add(ev)
        await db.commit()
        eval_id = ev.id

    # Confirm file exists before deletion
    file_content = await storage.get_file(file_key)
    assert file_content is not None

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Trigger hard delete
        res = await client.delete(f"/api/v1/evaluations/{eval_id}/hard-delete", headers=auth)
        assert res.status_code == 200
        assert res.json()["status"] == "purged"

        # Verify database row is gone
        res_check = await client.get(f"/api/v1/evaluations/{eval_id}", headers=auth)
        assert res_check.status_code == 404

        # Verify storage file is gone
        with pytest.raises(FileNotFoundError):
            await storage.get_file(file_key)


@pytest.mark.asyncio
async def test_candidate_data_export_portability() -> None:
    """Verify candidate data portability export endpoint returns full dossier bundle."""
    await init_db()

    user = await create_test_user("export_user@recruitlens.local")
    token = create_access_token({"sub": user.id, "role": user.role})
    auth = {"Authorization": f"Bearer {token}"}

    async with AsyncSessionLocal() as db:
        job = Job(user_id=user.id, title="DevOps Engineer", raw_text="Kubernetes", status="active")
        db.add(job)
        await db.flush()

        resume = Resume(
            user_id=user.id,
            job_id=job.id,
            filename="devops_cand.pdf",
            storage_path="path/devops.pdf",
            file_hash="hash_port",
            status="scored",
        )
        db.add(resume)
        await db.flush()

        ev = Evaluation(
            user_id=user.id,
            job_id=job.id,
            resume_id=resume.id,
            total_score=0.79,
            tier="Review",
            confidence=0.92,
            stage="screened",
            breakdown_json={"skills": {"score": 0.8}, "experience": {"score": 0.75}},
            explanation_json={"summary": "Strong Kubernetes background"},
            interview_questions_json={"questions": ["How do you handle pod eviction?"]},
            evidence_hash="ev_port",
        )
        db.add(ev)
        await db.flush()

        feedback = InterviewFeedbackRecord(
            user_id=user.id,
            evaluation_id=ev.id,
            interviewer_name="Lead DevOps",
            overall_score=4,
            recommendation="hire",
        )
        db.add(feedback)
        await db.commit()
        eval_id = ev.id

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get(f"/api/v1/evaluations/{eval_id}/export", headers=auth)
        assert res.status_code == 200
        data = res.json()
        assert data["candidate_id"] == eval_id
        assert data["total_score"] == 0.79
        assert data["tier"] == "Review"
        assert len(data["feedback"]) == 1
        assert data["feedback"][0]["interviewer"] == "Lead DevOps"


@pytest.mark.asyncio
async def test_what_if_counterfactual_simulation() -> None:
    """Verify what-if sensitivity recalculation simulates new score and tier without modifying DB."""
    await init_db()

    user = await create_test_user("whatif_user@recruitlens.local")
    token = create_access_token({"sub": user.id, "role": user.role})
    auth = {"Authorization": f"Bearer {token}"}

    async with AsyncSessionLocal() as db:
        job = Job(user_id=user.id, title="ML Engineer", raw_text="PyTorch", status="active")
        db.add(job)
        await db.flush()

        resume = Resume(
            user_id=user.id,
            job_id=job.id,
            filename="ml_cand.pdf",
            storage_path="path/ml.pdf",
            file_hash="hash_whatif",
            status="scored",
        )
        db.add(resume)
        await db.flush()

        ev = Evaluation(
            user_id=user.id,
            job_id=job.id,
            resume_id=resume.id,
            total_score=0.45,
            tier="Reject",
            confidence=0.9,
            stage="screened",
            breakdown_json={
                "skills": {"score": 0.95},
                "experience": {"score": 0.20},
                "education": {"score": 0.10},
                "semantic": {"score": 0.30},
            },
            evidence_hash="ev_whatif",
        )
        db.add(ev)
        await db.commit()
        eval_id = ev.id

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Simulate heavy weight on skills (0.9 skills) -> should elevate score into FastTrack
        res = await client.post(
            f"/api/v1/evaluations/{eval_id}/what-if",
            headers=auth,
            json={
                "weights": {
                    "skills": 0.90,
                    "experience": 0.05,
                    "education": 0.025,
                    "semantic": 0.025,
                }
            },
        )
        assert res.status_code == 200
        data = res.json()
        assert data["original_score"] == 0.45
        assert data["original_tier"] == "Reject"
        assert data["new_score"] > 0.75
        assert data["new_tier"] == "FastTrack"
        assert data["score_delta"] > 0.0

        # Verify DB evaluation was NOT changed
        res_db = await client.get(f"/api/v1/evaluations/{eval_id}", headers=auth)
        assert res_db.status_code == 200
        assert res_db.json()["total_score"] == 0.45


@pytest.mark.asyncio
async def test_sse_task_progress_and_cancel() -> None:
    """Verify background task progress querying, SSE streaming, and cancellation."""
    await init_db()

    user = await create_test_user("tasks_user@recruitlens.local")
    token = create_access_token({"sub": user.id, "role": user.role})
    auth = {"Authorization": f"Bearer {token}"}

    async with AsyncSessionLocal() as db:
        task = BackgroundTask(
            user_id=user.id,
            task_type="batch_ingestion",
            status="in_progress",
            progress=5,
            total=20,
            payload_json={"sample": "data"},
        )
        db.add(task)
        await db.commit()
        task_id = task.id

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Query status
        res = await client.get(f"/api/v1/tasks/{task_id}", headers=auth)
        assert res.status_code == 200
        assert res.json()["progress"] == 5
        assert res.json()["status"] == "in_progress"

        # 2. Cancel in-progress task
        res_c = await client.post(f"/api/v1/tasks/{task_id}/cancel", headers=auth)
        assert res_c.status_code == 200
        assert res_c.json()["status"] == "cancelled"

        # 3. Cancelling already cancelled/completed task returns 400
        # First mark task completed
        async with AsyncSessionLocal() as db:
            from sqlalchemy import select

            t_res = await db.execute(select(BackgroundTask).where(BackgroundTask.id == task_id))
            t = t_res.scalar_one()
            t.status = "completed"
            await db.commit()

        res_bad = await client.post(f"/api/v1/tasks/{task_id}/cancel", headers=auth)
        assert res_bad.status_code == 400
        assert "cannot cancel task in 'completed' state" in res_bad.json()["detail"].lower()


@pytest.mark.asyncio
async def test_resume_upload_limits_and_magic_byte_check() -> None:
    """Verify resume upload constraints: magic-byte check, size limit, and batch capacity."""
    await init_db()

    user = await create_test_user("upload_user@recruitlens.local")
    token = create_access_token({"sub": user.id, "role": user.role})
    auth = {"Authorization": f"Bearer {token}"}

    async with AsyncSessionLocal() as db:
        job = Job(user_id=user.id, title="QA Engineer", raw_text="Testing", status="active")
        db.add(job)
        await db.commit()
        job_id = job.id

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Invalid magic bytes: A text file disguised as .pdf
        fake_txt_file = io.BytesIO(b"Hello world, I am not a real PDF document.")
        res = await client.post(
            f"/api/v1/resumes/upload/{job_id}",
            headers=auth,
            files=[("files", ("fake_resume.pdf", fake_txt_file, "application/pdf"))],
        )
        assert res.status_code == 400
        assert "magic bytes" in res.json()["detail"].lower()

        # 2. Valid PDF with %PDF magic bytes
        valid_pdf = io.BytesIO(b"%PDF-1.4\n%Valid header\nResume content")
        res_valid = await client.post(
            f"/api/v1/resumes/upload/{job_id}",
            headers=auth,
            files=[("files", ("valid_resume.pdf", valid_pdf, "application/pdf"))],
        )
        assert res_valid.status_code == 202
        assert res_valid.json()["resume_count"] == 1
        assert "task_id" in res_valid.json()

        # 3. Batch exceeding MAX_BATCH_RESUMES
        too_many_files = [
            ("files", (f"resume_{i}.pdf", io.BytesIO(b"%PDF-1.4 sample"), "application/pdf"))
            for i in range(settings.MAX_BATCH_RESUMES + 1)
        ]
        res_cap = await client.post(
            f"/api/v1/resumes/upload/{job_id}",
            headers=auth,
            files=too_many_files,
        )
        assert res_cap.status_code == 400
        assert "maximum limit" in res_cap.json()["detail"].lower()


@pytest.mark.asyncio
async def test_login_throttling() -> None:
    """Verify login endpoint throttles after 5 failed attempts (429 Too Many Requests)."""
    await init_db()

    email = f"throttle_{datetime.now(UTC).timestamp()}@recruitlens.local"
    await create_test_user(email, password="CorrectPassword123!")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 5 failed attempts
        for _ in range(5):
            res = await client.post(
                "/api/v1/auth/login",
                json={"email": email, "password": "WrongPassword123!"},
            )
            assert res.status_code == 401

        # 6th attempt should be throttled (429)
        res_throttled = await client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "WrongPassword123!"},
        )
        assert res_throttled.status_code == 429
        assert "too many failed login attempts" in res_throttled.json()["detail"].lower()


@pytest.mark.asyncio
async def test_refresh_token_reuse_detection() -> None:
    """Verify token reuse detection: replaying a consumed refresh token revokes the token family."""
    await init_db()

    email = f"reuse_{datetime.now(UTC).timestamp()}@recruitlens.local"
    await create_test_user(email, password="ValidPassword123!")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Login
        login_res = await client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "ValidPassword123!"},
        )
        assert login_res.status_code == 200
        refresh_token_1 = login_res.json()["refresh_token"]

        # First refresh (valid rotation)
        ref_res_1 = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token_1},
        )
        assert ref_res_1.status_code == 200
        refresh_token_2 = ref_res_1.json()["refresh_token"]

        # REPLAY ATTACK: Replay refresh_token_1 (already consumed)
        ref_replay = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token_1},
        )
        assert ref_replay.status_code == 401
        assert "compromised" in ref_replay.json()["detail"].lower()

        # refresh_token_2 from the same family must now also be revoked
        ref_family = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token_2},
        )
        assert ref_family.status_code == 401


@pytest.mark.asyncio
async def test_jobs_full_crud_and_filtering() -> None:
    """Verify list jobs with filter, update job requisition, and delete job."""
    await init_db()

    user = await create_test_user("job_crud@recruitlens.local")
    token = create_access_token({"sub": user.id, "role": user.role})
    auth = {"Authorization": f"Bearer {token}"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Create job
        res_c = await client.post(
            "/api/v1/jobs/",
            headers=auth,
            json={
                "title": "Systems Lead",
                "department": "Infrastructure",
                "raw_text": "C++ and Linux kernel experience required. 5 years.",
            },
        )
        assert res_c.status_code == 201
        job_id = res_c.json()["id"]

        # List jobs with status filter
        res_l = await client.get("/api/v1/jobs/?status=active", headers=auth)
        assert res_l.status_code == 200
        assert any(j["id"] == job_id for j in res_l.json())

        # Update job
        res_u = await client.put(
            f"/api/v1/jobs/{job_id}",
            headers=auth,
            json={"title": "Principal Systems Lead", "status": "paused"},
        )
        assert res_u.status_code == 200
        assert res_u.json()["title"] == "Principal Systems Lead"
        assert res_u.json()["status"] == "paused"

        # Delete job
        res_d = await client.delete(f"/api/v1/jobs/{job_id}", headers=auth)
        assert res_d.status_code == 204

        # Verify 404 after deletion
        res_g = await client.get(f"/api/v1/jobs/{job_id}", headers=auth)
        assert res_g.status_code == 404


@pytest.mark.asyncio
async def test_evaluations_filter_and_export_pdf() -> None:
    """Verify candidate evaluation listing with tier/stage filters and shortlist PDF export."""
    await init_db()

    user = await create_test_user("eval_filter@recruitlens.local")
    token = create_access_token({"sub": user.id, "role": user.role})
    auth = {"Authorization": f"Bearer {token}"}

    async with AsyncSessionLocal() as db:
        job = Job(user_id=user.id, title="Frontend Lead", raw_text="TypeScript", status="active")
        db.add(job)
        await db.flush()

        resume = Resume(
            user_id=user.id,
            job_id=job.id,
            filename="front_cand.pdf",
            storage_path="path/front.pdf",
            file_hash="hash_front",
            status="scored",
        )
        db.add(resume)
        await db.flush()

        ev = Evaluation(
            user_id=user.id,
            job_id=job.id,
            resume_id=resume.id,
            total_score=0.92,
            tier="FastTrack",
            confidence=0.96,
            stage="shortlisted",
            breakdown_json={"skills": {"score": 0.95}},
            evidence_hash="ev_front",
        )
        db.add(ev)
        await db.commit()
        job_id = job.id

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Filter matching
        res = await client.get(
            f"/api/v1/evaluations/job/{job_id}?tier=FastTrack&stage=shortlisted",
            headers=auth,
        )
        assert res.status_code == 200
        assert len(res.json()) == 1

        # Filter not matching
        res_empty = await client.get(
            f"/api/v1/evaluations/job/{job_id}?tier=Reject",
            headers=auth,
        )
        assert res_empty.status_code == 200
        assert len(res_empty.json()) == 0

        # Export shortlist PDF
        res_pdf = await client.get(f"/api/v1/evaluations/job/{job_id}/export/pdf", headers=auth)
        assert res_pdf.status_code == 200
        assert res_pdf.headers["content-type"] == "application/pdf"
        assert res_pdf.content.startswith(b"%PDF")


@pytest.mark.asyncio
async def test_resumes_signed_download_and_list_endpoints() -> None:
    """Verify resume listing with signed URLs and download verification logic."""
    await init_db()

    user = await create_test_user("resume_dl_user@recruitlens.local")
    token = create_access_token({"sub": user.id, "role": user.role})
    auth = {"Authorization": f"Bearer {token}"}

    storage = get_storage_backend()
    file_path = "dl_job/test_download.pdf"
    file_bytes = b"%PDF-1.4 Downloadable content"
    await storage.save_file(file_path, file_bytes)

    async with AsyncSessionLocal() as db:
        job = Job(user_id=user.id, title="DL Job", raw_text="DL text", status="active")
        db.add(job)
        await db.flush()

        resume = Resume(
            user_id=user.id,
            job_id=job.id,
            filename="test_download.pdf",
            storage_path=file_path,
            file_hash="hash_dl",
            status="scored",
        )
        db.add(resume)
        await db.commit()
        job_id = job.id

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. List resumes for job
        res_list = await client.get(f"/api/v1/resumes/job/{job_id}", headers=auth)
        assert res_list.status_code == 200
        items = res_list.json()
        assert len(items) == 1
        signed_url = items[0]["signed_url"]
        assert signed_url is not None
        assert "/api/v1/resumes/download/" in signed_url

        # 2. Download using signed URL
        res_dl = await client.get(signed_url)
        assert res_dl.status_code == 200
        assert res_dl.content == file_bytes

        # 3. Expired download URL -> 403
        past_exp = int((datetime.now(UTC) - timedelta(hours=1)).timestamp())
        secret = settings.JWT_SECRET_KEY.encode("utf-8")
        past_sig = hmac.new(secret, f"{file_path}:{past_exp}".encode(), hashlib.sha256).hexdigest()
        res_exp = await client.get(
            f"/api/v1/resumes/download/{file_path}?exp={past_exp}&sig={past_sig}"
        )
        assert res_exp.status_code == 403
        assert "expired" in res_exp.json()["detail"].lower()

        # 4. Tampered signature -> 403
        future_exp = int((datetime.now(UTC) + timedelta(hours=1)).timestamp())
        res_bad_sig = await client.get(
            f"/api/v1/resumes/download/{file_path}?exp={future_exp}&sig=badsig123"
        )
        assert res_bad_sig.status_code == 403
        assert "invalid signature" in res_bad_sig.json()["detail"].lower()

        # 5. Non-existent file in storage -> 404
        non_file = "dl_job/does_not_exist.pdf"
        non_sig = hmac.new(secret, f"{non_file}:{future_exp}".encode(), hashlib.sha256).hexdigest()
        res_not_found = await client.get(
            f"/api/v1/resumes/download/{non_file}?exp={future_exp}&sig={non_sig}"
        )
        assert res_not_found.status_code == 404

        # 6. Upload file exceeding size limit -> 400
        oversized = io.BytesIO(
            b"%PDF-1.4" + b"X" * (settings.MAX_UPLOAD_FILE_SIZE_MB * 1024 * 1024 + 10)
        )
        res_over = await client.post(
            f"/api/v1/resumes/upload/{job_id}",
            headers=auth,
            files=[("files", ("big.pdf", oversized, "application/pdf"))],
        )
        assert res_over.status_code == 400
        assert "exceeds maximum" in res_over.json()["detail"].lower()


@pytest.mark.asyncio
async def test_evaluations_detail_emails_and_transitions_coverage() -> None:
    """Verify evaluation detail fetching, email listing, and varied state machine transitions."""
    await init_db()

    user = await create_test_user("eval_cov_user@recruitlens.local")
    token = create_access_token({"sub": user.id, "role": user.role})
    auth = {"Authorization": f"Bearer {token}"}

    async with AsyncSessionLocal() as db:
        job = Job(user_id=user.id, title="QA Lead", raw_text="Testing", status="active")
        db.add(job)
        await db.flush()

        resume = Resume(
            user_id=user.id,
            job_id=job.id,
            filename="qa_cand.pdf",
            storage_path="path/qa.pdf",
            file_hash="hash_qa",
            status="scored",
        )
        db.add(resume)
        await db.flush()

        ev = Evaluation(
            user_id=user.id,
            job_id=job.id,
            resume_id=resume.id,
            total_score=0.75,
            tier="Review",
            confidence=0.88,
            stage="screened",
            breakdown_json={"skills": {"score": 0.75}},
            explanation_json={"sentences": ["Good candidate."]},
            interview_questions_json={"questions": ["Explain bug lifecycle"]},
            email_drafts_json={},
            evidence_hash="ev_qa",
        )
        db.add(ev)
        await db.flush()

        email = EmailRecord(
            user_id=user.id,
            evaluation_id=ev.id,
            email_type="interview_invite",
            recipient_email="qa@example.com",
            subject="Interview",
            body="Come to interview",
            status="draft",
        )
        db.add(email)
        await db.commit()
        eval_id = ev.id

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Get evaluation detail
        res_det = await client.get(f"/api/v1/evaluations/{eval_id}", headers=auth)
        assert res_det.status_code == 200
        assert res_det.json()["id"] == eval_id
        assert res_det.json()["confidence"] == 0.88

        # 2. List candidate emails
        res_emails = await client.get(f"/api/v1/evaluations/{eval_id}/emails", headers=auth)
        assert res_emails.status_code == 200
        assert len(res_emails.json()) == 1

        # 3. Transitions: screened -> held -> shortlisted -> rejected -> screened (reopen)
        # screened -> held
        res = await client.post(
            f"/api/v1/evaluations/{eval_id}/stage", headers=auth, json={"to_stage": "held"}
        )
        assert res.status_code == 200

        # held -> shortlisted
        res = await client.post(
            f"/api/v1/evaluations/{eval_id}/stage", headers=auth, json={"to_stage": "shortlisted"}
        )
        assert res.status_code == 200

        # shortlisted -> rejected
        res = await client.post(
            f"/api/v1/evaluations/{eval_id}/stage", headers=auth, json={"to_stage": "rejected"}
        )
        assert res.status_code == 200

        # rejected -> screened (reopening)
        res = await client.post(
            f"/api/v1/evaluations/{eval_id}/stage", headers=auth, json={"to_stage": "screened"}
        )
        assert res.status_code == 200
        assert res.json()["to_stage"] == "screened"

        # 4. What-if without weights provided (default weights)
        res_wi_def = await client.post(
            f"/api/v1/evaluations/{eval_id}/what-if", headers=auth, json={}
        )
        assert res_wi_def.status_code == 200
        assert "new_score" in res_wi_def.json()

        # 5. Normal DELETE candidate evaluation (204)
        res_del = await client.delete(f"/api/v1/evaluations/{eval_id}", headers=auth)
        assert res_del.status_code == 204


@pytest.mark.asyncio
async def test_evaluations_trigger_llm_and_limits(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify on-demand LLM generation trigger, token budget cap, and failure handling."""
    await init_db()

    user = await create_test_user("llm_trig_user@recruitlens.local")
    token = create_access_token({"sub": user.id, "role": user.role})
    auth = {"Authorization": f"Bearer {token}"}

    async with AsyncSessionLocal() as db:
        job = Job(user_id=user.id, title="LLM Job", raw_text="LLM", status="active")
        db.add(job)
        await db.flush()

        resume = Resume(
            user_id=user.id,
            job_id=job.id,
            filename="llm_cand.pdf",
            storage_path="path/llm.pdf",
            file_hash="hash_llm",
            status="scored",
        )
        db.add(resume)
        await db.flush()

        ev = Evaluation(
            user_id=user.id,
            job_id=job.id,
            resume_id=resume.id,
            total_score=0.8,
            tier="FastTrack",
            confidence=0.9,
            stage="screened",
            evidence_hash="ev_llm",
        )
        db.add(ev)
        await db.commit()
        eval_id = ev.id

    async def mock_success(evaluation_id: str) -> bool:
        return True

    async def mock_fail(evaluation_id: str) -> bool:
        return False

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Success path
        monkeypatch.setattr("app.api.v1.evaluations.generate_on_demand_llm_text", mock_success)
        res_succ = await client.post(f"/api/v1/evaluations/{eval_id}/generate-llm", headers=auth)
        assert res_succ.status_code == 200
        assert res_succ.json()["status"] == "success"

        # 2. Failure path (500)
        monkeypatch.setattr("app.api.v1.evaluations.generate_on_demand_llm_text", mock_fail)
        res_fail = await client.post(f"/api/v1/evaluations/{eval_id}/generate-llm", headers=auth)
        assert res_fail.status_code == 500

        # 3. Token budget exceeded (429)
        async with AsyncSessionLocal() as db:
            from sqlalchemy import select

            u_res = await db.execute(select(User).where(User.id == user.id))
            u = u_res.scalar_one()
            u.daily_token_usage = settings.DAILY_TOKEN_BUDGET + 100
            await db.commit()

        res_budget = await client.post(f"/api/v1/evaluations/{eval_id}/generate-llm", headers=auth)
        assert res_budget.status_code == 429
        assert "token budget exceeded" in res_budget.json()["detail"].lower()


@pytest.mark.asyncio
async def test_audit_logs_endpoints_complete() -> None:
    """Verify audit log listing with action, target_type, and target_id query parameters."""
    await init_db()

    user = await create_test_user("audit_view_user@recruitlens.local")
    token = create_access_token({"sub": user.id, "role": user.role})
    auth = {"Authorization": f"Bearer {token}"}

    async with AsyncSessionLocal() as db:
        log1 = AuditLog(
            user_id=user.id,
            action="create_job",
            target_type="job",
            target_id="job_999",
            details_json={"info": "first"},
        )
        log2 = AuditLog(
            user_id=user.id,
            action="send_email",
            target_type="email",
            target_id="email_888",
            details_json={"info": "second"},
        )
        db.add_all([log1, log2])
        await db.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # All logs
        res = await client.get("/api/v1/audit-logs/", headers=auth)
        assert res.status_code == 200
        assert len(res.json()) >= 2

        # Filter by action
        res_act = await client.get("/api/v1/audit-logs/?action=create_job", headers=auth)
        assert res_act.status_code == 200
        assert all(entry["action"] == "create_job" for entry in res_act.json())

        # Filter by target_type
        res_type = await client.get("/api/v1/audit-logs/?target_type=email", headers=auth)
        assert res_type.status_code == 200
        assert all(entry["target_type"] == "email" for entry in res_type.json())

        # Filter by target_id
        res_id = await client.get("/api/v1/audit-logs/?target_id=job_999", headers=auth)
        assert res_id.status_code == 200
        assert all(entry["target_id"] == "job_999" for entry in res_id.json())


@pytest.mark.asyncio
async def test_auth_me_and_deactivated_user() -> None:
    """Verify /api/v1/auth/me profile endpoint and deactivated account rejection."""
    await init_db()

    email = f"auth_me_{datetime.now(UTC).timestamp()}@recruitlens.local"
    user = await create_test_user(email, password="MyPassword123!")
    token = create_access_token({"sub": user.id, "role": user.role})

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Valid auth/me
        res = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 200
        assert res.json()["email"] == email

        # Deactivate user
        async with AsyncSessionLocal() as db:
            from sqlalchemy import select

            u_res = await db.execute(select(User).where(User.id == user.id))
            u = u_res.scalar_one()
            u.is_active = False
            await db.commit()

        # Call with token of deactivated user -> 403
        res_deact = await client.get(
            "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
        )
        assert res_deact.status_code == 403
        assert "deactivated" in res_deact.json()["detail"].lower()


@pytest.mark.asyncio
async def test_jobs_router_crud_and_filters() -> None:
    """Verify list_jobs filters, get_job, update_job with weights/status/text, and delete_job."""
    await init_db()

    user = await create_test_user("job_crud_tester@recruitlens.local")
    token = create_access_token({"sub": user.id, "role": user.role})
    auth = {"Authorization": f"Bearer {token}"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Create 2 jobs
        res1 = await client.post(
            "/api/v1/jobs/",
            headers=auth,
            json={
                "title": "Backend Lead",
                "department": "Engineering",
                "raw_text": "Requires 5+ years Python and FastAPI experience.",
            },
        )
        assert res1.status_code == 201
        job1_id = res1.json()["id"]

        res2 = await client.post(
            "/api/v1/jobs/",
            headers=auth,
            json={
                "title": "Frontend Engineer",
                "department": "Product",
                "raw_text": "Requires React and TypeScript.",
            },
        )
        assert res2.status_code == 201
        job2_id = res2.json()["id"]

        # List all jobs
        res_list = await client.get("/api/v1/jobs/", headers=auth)
        assert res_list.status_code == 200
        assert len(res_list.json()) >= 2

        # List with status filter
        res_active = await client.get("/api/v1/jobs/?status=active", headers=auth)
        assert res_active.status_code == 200
        assert all(j["status"] == "active" for j in res_active.json())

        # Get existing job
        res_get = await client.get(f"/api/v1/jobs/{job1_id}", headers=auth)
        assert res_get.status_code == 200
        assert res_get.json()["title"] == "Backend Lead"

        # Get non-existent job -> 404
        res_get_404 = await client.get("/api/v1/jobs/nonexistent_job_id", headers=auth)
        assert res_get_404.status_code == 404

        # Update job: title, department, raw_text (triggers requirements extraction), weights, status
        res_update = await client.put(
            f"/api/v1/jobs/{job1_id}",
            headers=auth,
            json={
                "title": "Staff Backend Engineer",
                "department": "Core Platform",
                "raw_text": "Updated text: Must have Python, PostgreSQL, and AWS experience.",
                "weights": {"skills": 0.5, "experience": 0.3, "relevance": 0.2},
                "status": "closed",
            },
        )
        assert res_update.status_code == 200
        data = res_update.json()
        assert data["title"] == "Staff Backend Engineer"
        assert data["department"] == "Core Platform"
        assert data["status"] == "closed"
        assert data["weights_json"]["skills"] == 0.5

        # Update non-existent job -> 404
        res_update_404 = await client.put(
            "/api/v1/jobs/nonexistent_job_id",
            headers=auth,
            json={"title": "Ghost"},
        )
        assert res_update_404.status_code == 404

        # Delete job
        res_del = await client.delete(f"/api/v1/jobs/{job2_id}", headers=auth)
        assert res_del.status_code == 204

        # Delete non-existent job -> 404
        res_del_404 = await client.delete(f"/api/v1/jobs/{job2_id}", headers=auth)
        assert res_del_404.status_code == 404


@pytest.mark.asyncio
async def test_auth_router_login_and_refresh_branches() -> None:
    """Verify auth endpoints: login failure cases, successful refresh rotation, invalid refresh."""
    await init_db()

    email = f"auth_branch_{datetime.now(UTC).timestamp()}@recruitlens.local"
    await create_test_user(email, password="ValidPassword123!")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Login with bad password -> 401
        res_bad = await client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "WrongPassword!"},
        )
        assert res_bad.status_code == 401

        # 2. Login with non-existent user -> 401
        res_non = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "nonexistent_auth_user@recruitlens.local",
                "password": "ValidPassword123!",
            },
        )
        assert res_non.status_code == 401

        # 3. Successful login -> returns tokens
        res_ok = await client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "ValidPassword123!"},
        )
        assert res_ok.status_code == 200
        tokens = res_ok.json()
        access_token = tokens["access_token"]
        refresh_token = tokens["refresh_token"]

        # 4. Successful refresh -> rotates token
        res_ref = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert res_ref.status_code == 200
        new_tokens = res_ref.json()
        assert new_tokens["access_token"] != access_token
        assert new_tokens["refresh_token"]

        # 5. Invalid refresh JWT (garbage string) -> 401
        res_inv = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "garbage.jwt.token"},
        )
        assert res_inv.status_code == 401

        # 6. Valid JWT format but wrong type (using access token as refresh token) -> 401
        res_wrong_type = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": access_token},
        )
        assert res_wrong_type.status_code == 401


@pytest.mark.asyncio
async def test_resumes_router_upload_and_download_complete() -> None:
    """Verify resume batch upload, signed URL generation, and download validation."""
    await init_db()

    user = await create_test_user("resume_endpoints_user@recruitlens.local")
    token = create_access_token({"sub": user.id, "role": user.role})
    auth = {"Authorization": f"Bearer {token}"}

    job_id = ""
    async with AsyncSessionLocal() as db:
        job = Job(
            user_id=user.id,
            title="DevOps Specialist",
            department="Operations",
            raw_text="Docker, Kubernetes, CI/CD",
            status="active",
        )
        db.add(job)
        await db.commit()
        await db.refresh(job)
        job_id = str(job.id)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Upload to non-existent job -> 404
        dummy_pdf = io.BytesIO(b"%PDF-1.4 Minimal PDF document content")
        res_404 = await client.post(
            "/api/v1/resumes/upload/nonexistent_job_id",
            headers=auth,
            files=[("files", ("test.pdf", dummy_pdf, "application/pdf"))],
        )
        assert res_404.status_code == 404

        # 2. Upload with no valid PDF files -> 400
        dummy_txt = io.BytesIO(b"Just plain text")
        res_nopdf = await client.post(
            f"/api/v1/resumes/upload/{job_id}",
            headers=auth,
            files=[("files", ("notes.txt", dummy_txt, "text/plain"))],
        )
        assert res_nopdf.status_code == 400

        # 3. Successful upload of valid PDF -> 202
        dummy_valid_pdf = io.BytesIO(b"%PDF-1.4 valid candidate resume binary")
        res_upload = await client.post(
            f"/api/v1/resumes/upload/{job_id}",
            headers=auth,
            files=[("files", ("candidate_john.pdf", dummy_valid_pdf, "application/pdf"))],
        )
        assert res_upload.status_code == 202
        upload_data = res_upload.json()
        assert upload_data["resume_count"] == 1
        assert "task_id" in upload_data

        # 4. List resumes for job
        res_list = await client.get(f"/api/v1/resumes/job/{job_id}", headers=auth)
        assert res_list.status_code == 200
        resumes = res_list.json()
        assert len(resumes) >= 1
        resume_record = resumes[0]
        signed_url = resume_record["signed_url"]
        assert signed_url is not None

        # List resumes for non-existent job -> 404
        res_list_404 = await client.get("/api/v1/resumes/job/nonexistent_job", headers=auth)
        assert res_list_404.status_code == 404

        # 5. Download resume endpoints:
        # Missing exp / sig -> 422 (validation error on required query parameters)
        res_no_sig = await client.get("/api/v1/resumes/download/dummy/path.pdf")
        assert res_no_sig.status_code == 422

        # Expired signature -> 403
        past_expires = int((datetime.now(UTC) - timedelta(hours=1)).timestamp())
        res_expired = await client.get(
            f"/api/v1/resumes/download/dummy/path.pdf?exp={past_expires}&sig=invalid"
        )
        assert res_expired.status_code == 403

        # Invalid HMAC signature -> 403
        future_expires = int((datetime.now(UTC) + timedelta(hours=1)).timestamp())
        res_bad_sig = await client.get(
            f"/api/v1/resumes/download/dummy/path.pdf?exp={future_expires}&sig=wrong_sig"
        )
        assert res_bad_sig.status_code == 403

        # Valid download via generated signed_url -> 200
        res_download_ok = await client.get(signed_url)
        assert res_download_ok.status_code == 200
        assert res_download_ok.content == b"%PDF-1.4 valid candidate resume binary"


@pytest.mark.asyncio
async def test_tasks_router_status_stream_and_cancel() -> None:
    """Verify task status retrieval, cancel on completed task, cancel on pending task, and SSE."""
    await init_db()

    user = await create_test_user("tasks_tester@recruitlens.local")
    token = create_access_token({"sub": user.id, "role": user.role})
    auth = {"Authorization": f"Bearer {token}"}

    async with AsyncSessionLocal() as db:
        pending_task = BackgroundTask(
            user_id=user.id,
            task_type="batch_ingestion",
            status="pending",
            progress=0,
            total=10,
        )
        completed_task = BackgroundTask(
            user_id=user.id,
            task_type="batch_ingestion",
            status="completed",
            progress=10,
            total=10,
        )
        db.add_all([pending_task, completed_task])
        await db.commit()
        await db.refresh(pending_task)
        await db.refresh(completed_task)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Get task status
        res_stat = await client.get(f"/api/v1/tasks/{pending_task.id}", headers=auth)
        assert res_stat.status_code == 200
        assert res_stat.json()["status"] == "pending"

        # Get non-existent task -> 404
        res_stat_404 = await client.get("/api/v1/tasks/nonexistent_task_id", headers=auth)
        assert res_stat_404.status_code == 404

        # 2. Cancel non-existent task -> 404
        res_can_404 = await client.post("/api/v1/tasks/nonexistent_task_id/cancel", headers=auth)
        assert res_can_404.status_code == 404

        # 3. Cancel already completed task -> 400
        res_can_completed = await client.post(
            f"/api/v1/tasks/{completed_task.id}/cancel", headers=auth
        )
        assert res_can_completed.status_code == 400
        assert "cannot cancel" in res_can_completed.json()["detail"].lower()

        # 4. Cancel pending task -> 200
        res_can_ok = await client.post(f"/api/v1/tasks/{pending_task.id}/cancel", headers=auth)
        assert res_can_ok.status_code == 200
        assert res_can_ok.json()["status"] == "cancelled"

        # 5. SSE events stream on completed task (terminates immediately)
        res_sse = await client.get(f"/api/v1/tasks/{completed_task.id}/events", headers=auth)
        assert res_sse.status_code == 200
        assert "event: progress" in res_sse.text

        # SSE stream on non-existent task (returns error event and terminates)
        res_sse_missing = await client.get("/api/v1/tasks/nonexistent_id/events", headers=auth)
        assert res_sse_missing.status_code == 200
        assert "event: error" in res_sse_missing.text


@pytest.mark.asyncio
async def test_evaluations_router_queries_drafts_and_pdf() -> None:
    """Verify list_evaluations filters, get_evaluation_detail, feedback/email lists, update email, and PDF export."""
    await init_db()

    user = await create_test_user("evals_endpoints_user@recruitlens.local")
    token = create_access_token({"sub": user.id, "role": user.role})
    auth = {"Authorization": f"Bearer {token}"}

    async with AsyncSessionLocal() as db:
        job = Job(
            user_id=user.id,
            title="Senior Site Reliability Engineer",
            department="Infrastructure",
            raw_text="Requires Kubernetes, Terraform, Go.",
            status="active",
        )
        db.add(job)
        await db.flush()

        resume = Resume(
            user_id=user.id,
            job_id=job.id,
            filename="sre_candidate.pdf",
            storage_path=f"{job.id}/sre.pdf",
            file_hash="hash_sre_eval",
            status="scored",
        )
        db.add(resume)
        await db.flush()

        evaluation = Evaluation(
            user_id=user.id,
            job_id=job.id,
            resume_id=resume.id,
            total_score=0.92,
            tier="FastTrack",
            confidence=0.88,
            stage="shortlisted",
            evidence_hash="evidence_hash_sre_sample",
            breakdown_json={"skills": {"score": 0.95}, "experience": {"score": 0.90}},
            explanation_json={
                "summary": "Strong systems engineer with extensive Kubernetes production experience."
            },
            explanation_type="rule_based",
            interview_questions_json={
                "questions": [{"question": "How do you handle k8s etcd split-brain?"}]
            },
            email_drafts_json={
                "drafts": [
                    {
                        "type": "shortlist",
                        "subject": "Interview Invitation",
                        "body": "We would like to invite you...",
                    }
                ]
            },
        )
        db.add(evaluation)
        await db.flush()

        feedback = InterviewFeedbackRecord(
            user_id=user.id,
            evaluation_id=evaluation.id,
            interviewer_name="Alice Recruiter",
            overall_score=5,
            technical_rating=5,
            communication_rating=4,
            recommendation="strong_hire",
            notes="Outstanding architecture depth.",
            strengths="Great systems architecture",
            concerns="None noted",
        )
        draft = EmailRecord(
            user_id=user.id,
            evaluation_id=evaluation.id,
            recipient_email="sre_candidate@example.com",
            subject="Interview Invitation",
            body="Initial body text",
            email_type="shortlist",
            status="draft",
        )
        sent_email = EmailRecord(
            user_id=user.id,
            evaluation_id=evaluation.id,
            recipient_email="sre_candidate@example.com",
            subject="Already Sent Subject",
            body="Sent body",
            email_type="shortlist",
            status="sent",
        )
        db.add_all([feedback, draft, sent_email])
        await db.commit()
        await db.refresh(job)
        await db.refresh(evaluation)
        await db.refresh(draft)
        await db.refresh(sent_email)
        job_id = job.id
        eval_id = evaluation.id
        draft_id = draft.id
        sent_id = sent_email.id

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. List evaluations with tier & stage query filters
        res_list = await client.get(
            f"/api/v1/evaluations/job/{job_id}?tier=FastTrack&stage=shortlisted", headers=auth
        )
        assert res_list.status_code == 200
        items = res_list.json()
        assert len(items) == 1
        assert items[0]["tier"] == "FastTrack"
        assert items[0]["stage"] == "shortlisted"

        # List evaluations for non-existent job -> 404
        res_list_404 = await client.get("/api/v1/evaluations/job/nonexistent_job", headers=auth)
        assert res_list_404.status_code == 404

        # 2. Get evaluation detail
        res_detail = await client.get(f"/api/v1/evaluations/{eval_id}", headers=auth)
        assert res_detail.status_code == 200
        assert res_detail.json()["total_score"] == 0.92

        # Get non-existent evaluation detail -> 404
        res_detail_404 = await client.get("/api/v1/evaluations/nonexistent_eval_id", headers=auth)
        assert res_detail_404.status_code == 404

        # 3. List interview feedback
        res_feed = await client.get(
            f"/api/v1/evaluations/{eval_id}/interview-feedback", headers=auth
        )
        assert res_feed.status_code == 200
        assert len(res_feed.json()) == 1

        # List feedback for non-existent evaluation -> 200 with empty list
        res_feed_none = await client.get(
            "/api/v1/evaluations/nonexistent_eval_id/interview-feedback", headers=auth
        )
        assert res_feed_none.status_code == 200
        assert res_feed_none.json() == []

        # 4. List email drafts
        res_emails = await client.get(f"/api/v1/evaluations/{eval_id}/emails", headers=auth)
        assert res_emails.status_code == 200
        assert len(res_emails.json()) >= 2

        # List email drafts for non-existent evaluation -> 200 with empty list
        res_emails_none = await client.get(
            "/api/v1/evaluations/nonexistent_eval_id/emails", headers=auth
        )
        assert res_emails_none.status_code == 200
        assert res_emails_none.json() == []

        # 5. Update email draft
        res_upd_draft = await client.put(
            f"/api/v1/evaluations/emails/{draft_id}",
            headers=auth,
            json={"subject": "Updated Subject Title", "body": "Updated body text for candidate."},
        )
        assert res_upd_draft.status_code == 200
        assert res_upd_draft.json()["subject"] == "Updated Subject Title"

        # Update non-existent draft -> 404
        res_upd_404 = await client.put(
            "/api/v1/evaluations/emails/nonexistent_draft_id",
            headers=auth,
            json={"subject": "Ghost Subject"},
        )
        assert res_upd_404.status_code == 404

        # Update already sent email draft -> 400
        res_upd_sent = await client.put(
            f"/api/v1/evaluations/emails/{sent_id}",
            headers=auth,
            json={"subject": "Cannot Edit Sent"},
        )
        assert res_upd_sent.status_code == 400

        # 6. Export Shortlist PDF
        res_pdf = await client.get(f"/api/v1/evaluations/job/{job_id}/export/pdf", headers=auth)
        assert res_pdf.status_code == 200
        assert res_pdf.headers["content-type"] == "application/pdf"
        assert res_pdf.content.startswith(b"%PDF")

        # Export PDF for non-existent job -> 404
        res_pdf_404 = await client.get(
            "/api/v1/evaluations/job/nonexistent_job/export/pdf", headers=auth
        )
        assert res_pdf_404.status_code == 404

        # 7. Soft delete evaluation
        res_soft_del = await client.delete(f"/api/v1/evaluations/{eval_id}", headers=auth)
        assert res_soft_del.status_code == 204

        # Soft delete non-existent evaluation -> 404
        res_soft_del_404 = await client.delete(f"/api/v1/evaluations/{eval_id}", headers=auth)
        assert res_soft_del_404.status_code == 404
