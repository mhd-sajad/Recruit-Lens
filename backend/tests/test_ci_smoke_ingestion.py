"""CI Smoke Test: End-to-end ingestion, scoring, ranking order, experience verification, and mock string leakage defense.

Uploads three synthetic resumes:
1. Strong candidate (high skills match, 6+ years experience)
2. Partial candidate (low skills match, 2 years experience)
3. Unrelated document (office equipment invoice)

Asserts:
- Ranking order: Strong > Partial > Unrelated
- Experience is verified and non-zero
- Non-resume / unrelated document is rejected or abstained
- Zero mock strings ("Alex Rivera", "Staff Backend Architect", "4 / 7", "8.5 yrs") leak into the output
- Blind mode properly redacts candidate identities
"""

import io

import pytest
from httpx import ASGITransport, AsyncClient
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from sqlalchemy import select

from app.auth.security import hash_password
from app.db.models import User
from app.db.session import AsyncSessionLocal, init_db
from app.main import app
from app.worker.tasks import process_batch_ingestion


def create_pdf_bytes(lines: list[str]) -> bytes:
    """Generate a valid, structured PDF document from text lines."""
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    y = 750
    for line in lines:
        c.drawString(50, y, line)
        y -= 16
        if y < 50:
            c.showPage()
            y = 750
    c.save()
    return buf.getvalue()


@pytest.fixture
def synthetic_pdfs() -> dict[str, bytes]:
    """Generate the three test PDF documents."""
    strong_text = [
        "Jane Doe",
        "Senior Distributed Systems Engineer",
        "jane.doe@example.com | (555) 234-5678 | San Francisco, CA",
        "",
        "PROFESSIONAL SUMMARY",
        "Senior Backend Engineer with 6+ years of verified production experience.",
        "",
        "EXPERIENCE",
        "Staff Systems Engineer at Acme Tech (2018 - 2024)",
        "- Designed high-throughput distributed microservices in Python and FastAPI.",
        "- Managed PostgreSQL database clusters with connection pooling and query optimization.",
        "- Orchestrated resilient container deployments on Docker and Kubernetes.",
        "- Implemented caching and message streaming using Redis.",
        "",
        "EDUCATION",
        "Bachelor of Science in Computer Science, Tech University (2014 - 2018)",
        "",
        "SKILLS",
        "Python, FastAPI, PostgreSQL, Docker, Redis, Kubernetes, Distributed Systems",
    ]

    partial_text = [
        "John Smith",
        "Junior Developer",
        "john.smith@example.com | (555) 876-5432 | Austin, TX",
        "",
        "PROFESSIONAL SUMMARY",
        "Junior software developer with 2 years of experience in Python scripting.",
        "",
        "EXPERIENCE",
        "Junior Python Developer at WebWorks LLC (2022 - 2024)",
        "- Wrote automated data collection and cleaning scripts in Python.",
        "- Assisted with basic SQL queries and report generation.",
        "",
        "EDUCATION",
        "Associate Degree in Computer Studies, City College (2020 - 2022)",
        "",
        "SKILLS",
        "Python, Git, Basic SQL",
    ]

    invoice_text = [
        "INVOICE #INV-2026-90412",
        "Date: October 15, 2026",
        "Vendor: Apex Office Supplies Direct Inc.",
        "Billed To: Corporate Procurement Dept",
        "",
        "LINE ITEMS:",
        "1. Ergonomic Mesh Office Chairs (Qty 4) - $350.00 each -> $1,400.00",
        "2. Adjustable Dual-Monitor Desk Mounts (Qty 2) - $95.00 each -> $190.00",
        "3. High-Speed USB-C Hub Adapters (Qty 6) - $45.00 each -> $270.00",
        "",
        "Subtotal: $1,860.00",
        "Sales Tax (8.25%): $153.45",
        "TOTAL AMOUNT DUE: $2,013.45",
        "",
        "PAYMENT TERMS: Net 30 days upon invoice receipt.",
        "Please remit payment via wire transfer to APEX SUPPLIES CORP.",
        "Thank you for your business!",
    ]

    return {
        "strong": create_pdf_bytes(strong_text),
        "partial": create_pdf_bytes(partial_text),
        "unrelated": create_pdf_bytes(invoice_text),
    }


@pytest.mark.asyncio
async def test_ci_smoke_ingestion_ranking_order_and_leak_defense(
    synthetic_pdfs: dict[str, bytes],
) -> None:
    """End-to-end smoke test validating ranking order, non-zero experience, invoice rejection, and leak-free output."""
    await init_db()

    # 1. Seed HR Deployment User
    test_email = "hr_smoke_tester@recruitlens.local"
    test_password = "SmokeTestPassword123!"
    async with AsyncSessionLocal() as session:
        user_res = await session.execute(select(User).where(User.email == test_email))
        user = user_res.scalar_one_or_none()
        if user is None:
            user = User(
                email=test_email,
                hashed_password=hash_password(test_password),
                full_name="Smoke Test Recruiter",
                role="recruiter",
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 2. Authenticate
        login_res = await client.post(
            "/api/v1/auth/login",
            json={"email": test_email, "password": test_password},
        )
        assert login_res.status_code == 200, f"Login failed: {login_res.text}"
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 3. Create Job Requisition
        job_payload = {
            "title": "Senior Backend Systems Engineer",
            "department": "Infrastructure",
            "raw_text": (
                "We are seeking a Senior Backend Engineer with 5+ years of verified experience in Python, "
                "FastAPI, and PostgreSQL. Experience with Docker and distributed systems is required. "
                "A Bachelor's degree in Computer Science is required."
            ),
            "weights": {"Python": 0.40, "FastAPI": 0.30, "PostgreSQL": 0.30},
        }
        create_res = await client.post("/api/v1/jobs/", json=job_payload, headers=headers)
        assert create_res.status_code == 201, f"Job creation failed: {create_res.text}"
        job_data = create_res.json()
        job_id = job_data["id"]

        # 4. Upload the three synthetic resumes
        files = [
            ("files", ("Jane_Doe_Senior_Backend.pdf", synthetic_pdfs["strong"], "application/pdf")),
            ("files", ("John_Smith_Junior_Dev.pdf", synthetic_pdfs["partial"], "application/pdf")),
            (
                "files",
                ("Invoice_Apex_Supplies_90412.pdf", synthetic_pdfs["unrelated"], "application/pdf"),
            ),
        ]
        upload_res = await client.post(
            f"/api/v1/resumes/upload/{job_id}", files=files, headers=headers
        )
        assert upload_res.status_code == 202, f"Resume upload failed: {upload_res.text}"
        upload_data = upload_res.json()
        assert upload_data["resume_count"] == 3
        task_id = upload_data["task_id"]

        # 5. Execute batch evaluation processing
        await process_batch_ingestion(task_id=task_id)

        # 6. Retrieve ranked evaluations
        eval_res = await client.get(f"/api/v1/evaluations/job/{job_id}", headers=headers)
        assert eval_res.status_code == 200, f"Fetch evaluations failed: {eval_res.text}"
        evals = eval_res.json()
        assert len(evals) == 3, f"Expected 3 evaluations, got {len(evals)}"

        # 7. Check Ranking Order: Strong > Partial > Unrelated
        strong_eval = next(
            (
                e
                for e in evals
                if "Jane" in (e.get("candidate_name") or "")
                or "jane" in e["candidate_filename"].lower()
            ),
            None,
        )
        partial_eval = next(
            (
                e
                for e in evals
                if "John" in (e.get("candidate_name") or "")
                or "john" in e["candidate_filename"].lower()
            ),
            None,
        )
        unrelated_eval = next(
            (e for e in evals if "invoice" in e["candidate_filename"].lower()), None
        )

        assert strong_eval is not None, "Strong candidate evaluation missing"
        assert partial_eval is not None, "Partial candidate evaluation missing"
        assert unrelated_eval is not None, "Unrelated invoice evaluation missing"

        # Explicit Score Ranking Assertions
        assert strong_eval["total_score"] > partial_eval["total_score"], (
            f"Strong score ({strong_eval['total_score']}) must exceed partial score ({partial_eval['total_score']})"
        )
        assert partial_eval["total_score"] > unrelated_eval["total_score"], (
            f"Partial score ({partial_eval['total_score']}) must exceed unrelated score ({unrelated_eval['total_score']})"
        )

        # 8. Experience Verification: Years of experience must not be 0 for real resumes
        assert strong_eval["years_experience"] is not None
        assert strong_eval["years_experience"] >= 5.0, (
            f"Strong candidate verified experience should be >= 5 years, got {strong_eval['years_experience']}"
        )

        assert partial_eval["years_experience"] is not None
        assert partial_eval["years_experience"] > 0, (
            f"Partial candidate verified experience must be non-zero, got {partial_eval['years_experience']}"
        )

        # 9. Non-Resume / Invoice Rejection Check: Document gate must reject or abstain
        assert unrelated_eval["tier"] in ("Abstain", "Reject"), (
            f"Invoice must be tiered as Abstain or Reject, got {unrelated_eval['tier']}"
        )

        # 10. Strict Mock String Leak Defense:
        # None of the evaluation records should leak hardcoded placeholder strings
        FORBIDDEN_MOCK_STRINGS = ["Alex Rivera", "Staff Backend Architect", "8.5 yrs", "4 / 7"]
        for e in evals:
            for forbidden in FORBIDDEN_MOCK_STRINGS:
                assert forbidden not in str(e["candidate_name"]), (
                    f"Leaked '{forbidden}' in candidate_name"
                )
                assert forbidden not in str(e["candidate_title"]), (
                    f"Leaked '{forbidden}' in candidate_title"
                )
                assert forbidden not in str(e["must_have_coverage"]), (
                    f"Leaked '{forbidden}' in must_have_coverage"
                )
                if forbidden == "8.5 yrs":
                    assert e["years_experience"] != 8.5, "Leaked 8.5 years placeholder"

        # 11. Blind Mode Redaction Verification:
        # When querying with blind_mode=True, candidate names and filenames must be fully masked
        blind_res = await client.get(
            f"/api/v1/evaluations/job/{job_id}?blind_mode=true", headers=headers
        )
        assert blind_res.status_code == 200
        blind_evals = blind_res.json()
        for be in blind_evals:
            assert be["candidate_name"].startswith("Candidate #"), (
                f"Candidate name not redacted in blind mode: {be['candidate_name']}"
            )
            assert be["candidate_filename"].startswith("candidate_"), (
                f"Candidate filename not redacted in blind mode: {be['candidate_filename']}"
            )
            assert "Jane" not in be["candidate_name"]
            assert "John" not in be["candidate_name"]
            assert "Doe" not in be["candidate_name"]
