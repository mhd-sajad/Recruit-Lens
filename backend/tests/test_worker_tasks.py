"""Integration tests for background worker tasks and resumability."""

from pathlib import Path

import pytest
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.auth.security import hash_password
from app.db.models import BackgroundTask, Evaluation, Job, Resume, User
from app.db.session import AsyncSessionLocal, init_db
from app.worker.tasks import generate_on_demand_llm_text, process_batch_ingestion


def create_sample_resume_pdf(path: Path, text: str) -> None:
    """Generate minimal PDF file for testing."""
    c = canvas.Canvas(str(path), pagesize=letter)
    y = 750
    for line in text.split("\n"):
        if line.strip():
            c.drawString(50, y, line.strip())
            y -= 18
    c.save()


@pytest.mark.asyncio
async def test_batch_ingestion_and_resumability(tmp_path: Path) -> None:
    """Verify batch ingestion worker parses, scores, updates progress, and supports resumability."""
    await init_db()

    # 1. Create 2 test PDFs
    pdf1 = tmp_path / "resume_alice.pdf"
    create_sample_resume_pdf(
        pdf1,
        (
            "Alice Engineer\n"
            "Email: alice@engineer.local\n"
            "Summary: Senior Python backend developer with 6 years experience in FastAPI, Docker, and PostgreSQL.\n"
            "Experience:\n"
            "Senior Backend Engineer at TechCorp (2018 - 2024)\n"
            "- Designed scalable microservices using FastAPI and PostgreSQL.\n"
            "- Managed Kubernetes clusters and CI/CD deployment pipelines.\n"
            "Education:\n"
            "Bachelor of Science in Computer Science, University of Washington (2014 - 2018)\n"
        ),
    )

    pdf2 = tmp_path / "resume_bob.pdf"
    create_sample_resume_pdf(
        pdf2,
        (
            "Bob Junior\n"
            "Email: bob@junior.local\n"
            "Summary: Junior web developer with 1 year experience in HTML, CSS, and basic JavaScript.\n"
            "Experience:\n"
            "Junior Web Intern at WebDev Inc (2023 - 2024)\n"
            "- Built static landing pages with HTML and CSS.\n"
            "Education:\n"
            "Associate Degree in Web Development, Community College (2021 - 2023)\n"
        ),
    )

    # 2. Seed storage and database records
    from app.core.storage import get_storage_backend

    storage = get_storage_backend()

    async with AsyncSessionLocal() as db:
        user = User(
            email="worker_tester@recruitlens.local",
            hashed_password=hash_password("Password123!"),
            full_name="Worker Tester",
            role="recruiter",
        )
        db.add(user)
        await db.flush()

        key1 = await storage.save_file(f"tests/{user.id}/resume_alice.pdf", pdf1.read_bytes())
        key2 = await storage.save_file(f"tests/{user.id}/resume_bob.pdf", pdf2.read_bytes())

        job = Job(
            user_id=user.id,
            title="Senior Backend Engineer",
            department="Engineering",
            raw_text=(
                "Senior Backend Engineer. Must have 5+ years of experience with Python, FastAPI, and PostgreSQL. "
                "Bachelor's degree in Computer Science required."
            ),
            requirements_json={
                "job_id": "test_job",
                "title": "Senior Backend Engineer",
                "raw_text": "Python FastAPI PostgreSQL",
                "must_have_skills": ["Python", "FastAPI", "PostgreSQL"],
                "nice_to_have_skills": ["Docker", "Kubernetes"],
                "min_experience_years": 5.0,
                "preferred_experience_years": 7.0,
                "minimum_education_level": "Bachelor's",
            },
            weights_json={"skills": 0.5, "experience": 0.3, "education": 0.2},
        )
        db.add(job)
        await db.flush()

        res1 = Resume(
            user_id=user.id,
            job_id=job.id,
            filename="resume_alice.pdf",
            file_hash="hash_alice_123",
            storage_path=key1,
            status="uploaded",
        )
        res2 = Resume(
            user_id=user.id,
            job_id=job.id,
            filename="resume_bob.pdf",
            file_hash="hash_bob_456",
            storage_path=key2,
            status="uploaded",
        )
        db.add_all([res1, res2])
        await db.flush()

        task = BackgroundTask(
            user_id=user.id,
            task_type="batch_ingestion",
            status="pending",
            progress=0,
            total=2,
            payload_json={"job_id": job.id},
            result_json={},
        )
        db.add(task)
        await db.commit()
        await db.refresh(task)
        task_id = task.id
        user_id = user.id
        job_id = job.id

    # 3. Execute batch ingestion task
    await process_batch_ingestion(task_id)

    # 4. Verify completion
    async with AsyncSessionLocal() as db:
        task_res = await db.execute(select(BackgroundTask).where(BackgroundTask.id == task_id))
        completed_task = task_res.scalar_one()
        assert completed_task.status == "completed"
        assert completed_task.progress == 2
        assert completed_task.total == 2

        # Verify evaluations created
        evals_res = await db.execute(
            select(Evaluation)
            .options(selectinload(Evaluation.resume))
            .where(Evaluation.job_id == job_id, Evaluation.user_id == user_id)
        )
        evals = evals_res.scalars().all()
        assert len(evals) == 2

        alice_eval = next(e for e in evals if e.resume.filename == "resume_alice.pdf")
        assert alice_eval.total_score >= 0.50
        assert alice_eval.tier in ["FastTrack", "Review", "Strong Fit", "Interview"]
        assert len(alice_eval.explanation_json["sentences"]) >= 3

        # 5. Test Resumability: Run task again
        # It should see both are already evaluated and skip cleanly
        task2 = BackgroundTask(
            user_id=user_id,
            task_type="batch_ingestion",
            status="pending",
            progress=0,
            total=2,
            payload_json={"job_id": job_id},
            result_json={},
        )
        db.add(task2)
        await db.commit()
        await db.refresh(task2)
        task2_id = task2.id

    await process_batch_ingestion(task2_id)

    async with AsyncSessionLocal() as db:
        t2_res = await db.execute(select(BackgroundTask).where(BackgroundTask.id == task2_id))
        completed_t2 = t2_res.scalar_one()
        assert completed_t2.status == "completed"
        assert completed_t2.progress == 2

        # Test on-demand LLM generation
        success = await generate_on_demand_llm_text(alice_eval.id, user_id)
        assert success is True

        ev_updated = (
            await db.execute(select(Evaluation).where(Evaluation.id == alice_eval.id))
        ).scalar_one()
        assert ev_updated.llm_generated is True
        assert len(ev_updated.interview_questions_json["questions"]) > 0
