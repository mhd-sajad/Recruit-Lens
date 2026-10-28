"""Seed script to populate database with realistic demo tenant, recruiter, JDs, and 15 candidate resumes."""

import asyncio
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from sqlalchemy import select

from app.auth.security import hash_password
from app.config import settings
from app.core.jd_requirements import extract_job_requirements
from app.core.taxonomy import SkillTaxonomy
from app.db.base import Base
from app.db.models import BackgroundTask, Evaluation, Job, Resume, Tenant, User
from app.db.session import AsyncSessionLocal, engine, init_db
from app.worker.tasks import process_batch_ingestion


def create_pdf(path: Path, text: str) -> None:
    """Generate clean PDF resume file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(path), pagesize=letter)
    y = 750
    for line in text.strip().split("\n"):
        line_s = line.strip()
        if line_s:
            c.drawString(50, y, line_s)
            y -= 16
            if y < 50:
                c.showPage()
                y = 750
    c.save()


# 15 Synthetic candidate resume definitions across 4 tiers
CANDIDATES = [
    # --- STRONG FIT (Tier 1) ---
    {
        "filename": "01_sarah_chen_staff_swe.pdf",
        "text": """
Sarah Chen
Email: sarah.chen@clouddev.local | Phone: +1-415-555-0101 | San Francisco, CA
Summary: Staff Full-Stack Engineer with 8 years of production experience architecting high-throughput distributed systems in Python, FastAPI, React, and TypeScript.
Experience:
Staff Software Engineer, CloudScale Systems (2020 - Present)
- Architected enterprise cloud microservices using FastAPI, Python, Docker, and PostgreSQL handling 45M daily requests.
- Led migration of legacy UI to React 18, TypeScript, and Tailwind CSS, improving Core Web Vitals by 42%.
- Integrated Redis caching and Kafka streaming pipelines for real-time analytics.
Senior Backend Engineer, DataStream Corp (2016 - 2020)
- Designed resilient RESTful APIs using Python, SQLAlchemy, and AWS ECS.
- Mentored 6 junior engineers and standardized CI/CD automated test suites.
Education:
Master of Science in Computer Science, Stanford University (2014 - 2016)
Bachelor of Science in Computer Engineering, UC Berkeley (2010 - 2014)
Skills: Python, FastAPI, React, TypeScript, Docker, PostgreSQL, Redis, Kubernetes, AWS, Git
""",
    },
    {
        "filename": "02_marcus_vance_lead_ml.pdf",
        "text": """
Marcus Vance
Email: marcus.vance@ai-labs.local | Phone: +1-206-555-0199 | Seattle, WA
Summary: Lead Machine Learning Engineer with 7 years experience deploying NLP transformer pipelines, PyTorch models, and real-time semantic search microservices.
Experience:
Lead Machine Learning Engineer, OmniSearch AI (2021 - Present)
- Deployed quantized ONNX transformer models on CPU/GPU clusters achieving 18ms latency for 5M daily queries.
- Engineered hybrid BM25 and dense embedding vector retrieval architectures using PyTorch and Hugging Face.
- Designed ML training pipelines with Scikit-Learn, XGBoost, and distributed data parallelization.
Senior Data Scientist, Nexus Analytics (2017 - 2021)
- Built predictive ranking models in Python, Pandas, and Scikit-Learn improving CTR by 28%.
Education:
Master of Science in Data Science, University of Washington (2015 - 2017)
Bachelor of Science in Mathematics, UCLA (2011 - 2015)
Skills: Python, Machine Learning, PyTorch, Natural Language Processing, Hugging Face, Transformers, Scikit-Learn, XGBoost, Docker
""",
    },
    {
        "filename": "03_elena_rostova_senior_fullstack.pdf",
        "text": """
Elena Rostova
Email: elena.rostova@devmail.local | Phone: +1-646-555-0144 | New York, NY
Summary: Senior Full-Stack Engineer with 6 years of expertise building scalable web platforms with Python, FastAPI, React, and PostgreSQL.
Experience:
Senior Software Engineer, FinTech Horizon (2021 - Present)
- Implemented real-time financial trading dashboards in React, TypeScript, and WebSockets.
- Built backend asynchronous microservices in FastAPI, SQLAlchemy, and PostgreSQL.
- Containerized workflows with Docker and established automated testing with Pytest.
Full-Stack Developer, AlphaByte Solutions (2018 - 2021)
- Developed responsive customer portal in React and Django.
Education:
Bachelor of Science in Computer Science, Columbia University (2014 - 2018)
Skills: Python, FastAPI, React, TypeScript, PostgreSQL, Docker, Git, CI/CD, Pytest
""",
    },
    {
        "filename": "04_david_kim_senior_backend.pdf",
        "text": """
David Kim
Email: david.kim@cloudsys.local | Phone: +1-512-555-0182 | Austin, TX
Summary: Senior Backend Engineer with 5.5 years specializing in cloud infrastructure, Python microservices, and distributed caching.
Experience:
Senior Backend Developer, Austin CloudWorks (2021 - Present)
- Built high-concurrency microservices using FastAPI, AsyncIO, and PostgreSQL.
- Spearheaded database optimization, partitioning, and indexing reducing P99 latency by 65%.
Software Engineer, TechVentures (2019 - 2021)
- Maintained Dockerized API gateways and integrated third-party payment gateways.
Education:
Bachelor of Science in Software Engineering, UT Austin (2015 - 2019)
Skills: Python, FastAPI, PostgreSQL, Docker, Redis, REST APIs, Microservices, Git
""",
    },
    # --- INTERVIEW (Tier 2) ---
    {
        "filename": "05_rachel_green_fullstack.pdf",
        "text": """
Rachel Green
Email: rachel.green@webstudio.local | Phone: +1-312-555-0112 | Chicago, IL
Summary: Full-Stack Developer with 4 years experience building web applications in Python, Django, and React.
Experience:
Software Engineer, Prairie Tech (2022 - Present)
- Developed SaaS web applications using Python, Django, and React.
- Wrote unit tests and managed Docker containers for staging environments.
Associate Developer, Midwest Digital (2020 - 2022)
- Built customer-facing landing pages and REST APIs in Python.
Education:
Bachelor of Science in Information Technology, University of Illinois (2016 - 2020)
Skills: Python, Django, React, JavaScript, PostgreSQL, Docker, Git
""",
    },
    {
        "filename": "06_tariq_ahmad_data_scientist.pdf",
        "text": """
Tariq Ahmad
Email: tariq.ahmad@datasci.local | Phone: +1-617-555-0133 | Boston, MA
Summary: Data Scientist with 4 years applying machine learning and statistical modeling to customer churn and NLP sentiment.
Experience:
Data Scientist, Beacon Analytics (2021 - Present)
- Trained classification models using Scikit-Learn and XGBoost on tabular customer datasets.
- Applied Hugging Face pre-trained transformers for text summarization tasks.
Junior Data Analyst, Vertex Labs (2020 - 2021)
- Built automated reporting dashboards using Python, Pandas, and SQL.
Education:
Bachelor of Science in Statistics, Boston University (2016 - 2020)
Skills: Python, Machine Learning, Scikit-Learn, Pandas, NLP, SQL, Git
""",
    },
    {
        "filename": "07_jessica_taylor_frontend_leaning.pdf",
        "text": """
Jessica Taylor
Email: jessica.taylor@frontend.local | Phone: +1-404-555-0177 | Atlanta, GA
Summary: Senior Frontend Engineer with 5 years experience in React, TypeScript, and modern CSS frameworks, expanding into Python backends.
Experience:
Senior Frontend Developer, Peach State Digital (2020 - Present)
- Engineered responsive React single-page applications with TypeScript and Tailwind CSS.
- Collaborated with backend teams to consume REST APIs; built lightweight mock services in Python.
Frontend Developer, Atlanta Agency (2019 - 2020)
- Designed interactive web interfaces using JavaScript and React.
Education:
Bachelor of Arts in Interactive Media, Georgia Tech (2015 - 2019)
Skills: React, TypeScript, JavaScript, HTML, CSS, Tailwind CSS, Python (basic), Git
""",
    },
    {
        "filename": "08_kevin_patel_backend_dev.pdf",
        "text": """
Kevin Patel
Email: kevin.patel@devcloud.local | Phone: +1-408-555-0129 | San Jose, CA
Summary: Backend Developer with 3.5 years experience in Python, Flask, and PostgreSQL database administration.
Experience:
Backend Engineer, Silicon Valley Apps (2021 - Present)
- Developed API backends using Python and Flask with PostgreSQL relational storage.
- Implemented user authentication with JWT and Bcrypt hashing.
Education:
Bachelor of Science in Computer Science, San Jose State University (2017 - 2021)
Skills: Python, Flask, PostgreSQL, Docker, Git, REST APIs
""",
    },
    # --- HOLD (Tier 3) ---
    {
        "filename": "09_brian_murphy_junior_dev.pdf",
        "text": """
Brian Murphy
Email: brian.murphy@freshgrad.local | Phone: +1-303-555-0188 | Denver, CO
Summary: Junior Software Developer with 1.5 years experience in Python scripting and basic React web interfaces.
Experience:
Junior Developer, Mile High Solutions (2023 - Present)
- Assisted backend team with bug fixes in Python scripts.
- Maintained internal documentation and automated testing runs.
Education:
Bachelor of Science in Computer Science, University of Colorado Boulder (2019 - 2023)
Skills: Python, JavaScript, React (basic), Git, SQL
""",
    },
    {
        "filename": "10_amanda_ross_qa_engineer.pdf",
        "text": """
Amanda Ross
Email: amanda.ross@quality.local | Phone: +1-602-555-0165 | Phoenix, AZ
Summary: Quality Assurance Engineer with 3 years writing automated test scripts in Python and Selenium.
Experience:
QA Automation Engineer, Desert Tech (2021 - Present)
- Developed end-to-end regression suites in Python, Pytest, and Selenium.
- Verified REST APIs using Postman and automated test scripts.
Education:
Bachelor of Science in Information Systems, Arizona State University (2017 - 2021)
Skills: Python, Pytest, Selenium, QA Testing, Git, REST APIs
""",
    },
    {
        "filename": "11_carlos_mendez_analyst.pdf",
        "text": """
Carlos Mendez
Email: carlos.mendez@metrics.local | Phone: +1-305-555-0141 | Miami, FL
Summary: Business Intelligence Analyst with 2 years analyzing operational metrics with SQL, Excel, and introductory Python.
Experience:
Data Analyst, Sunshine Logistics (2022 - Present)
- Extracted and cleaned customer shipment data using SQL queries.
- Built exploratory charts in Python using Matplotlib and Pandas.
Education:
Bachelor of Business Administration, Florida International University (2018 - 2022)
Skills: SQL, Excel, Python (introductory), Data Analysis, Tableau
""",
    },
    # --- REJECT / ABSTAIN (Tier 4) ---
    {
        "filename": "12_sophia_turner_marketing.pdf",
        "text": """
Sophia Turner
Email: sophia.turner@brandreach.local | Phone: +1-212-555-0155 | New York, NY
Summary: Digital Marketing Specialist with 5 years managing social media ad spend, SEO campaigns, and influencer partnerships.
Experience:
Marketing Manager, BrandReach Media (2021 - Present)
- Supervised Google Ads and Meta campaign budgets totaling $2.5M annually.
- Increased organic search traffic by 85% through content strategy and SEO.
Marketing Associate, Trend Agency (2019 - 2021)
- Managed email newsletters and brand PR events.
Education:
Bachelor of Arts in Communications, NYU (2015 - 2019)
Skills: Marketing, SEO, Social Media, Google Analytics, Copywriting, Content Strategy
""",
    },
    {
        "filename": "13_liam_o_connor_graphic_designer.pdf",
        "text": """
Liam O'Connor
Email: liam.design@creativelab.local | Phone: +1-310-555-0192 | Los Angeles, CA
Summary: Creative Graphic Designer with 6 years experience in Photoshop, Illustrator, and typography for print and digital brands.
Experience:
Senior Visual Designer, Studio West (2020 - Present)
- Created brand identity packages, logos, and marketing collateral in Figma and Adobe Suite.
Graphic Designer, Pixel Perfect (2018 - 2020)
- Designed posters, packaging, and digital display banners.
Education:
Bachelor of Fine Arts in Graphic Design, ArtCenter College of Design (2014 - 2018)
Skills: Adobe Photoshop, Illustrator, InDesign, Figma, Typography, Branding
""",
    },
    {
        "filename": "14_hannah_abbott_nurse.pdf",
        "text": """
Hannah Abbott
Email: hannah.abbott@healthcare.local | Phone: +1-615-555-0138 | Nashville, TN
Summary: Registered Nurse with 4 years experience in acute patient care, medication administration, and clinical documentation.
Experience:
Staff Nurse, Nashville General Hospital (2020 - Present)
- Provided comprehensive nursing care to surgical patients and managed post-operative recovery.
Education:
Bachelor of Science in Nursing, Vanderbilt University (2016 - 2020)
Skills: Patient Care, Clinical Nursing, Vital Signs, CPR, Electronic Medical Records
""",
    },
    {
        "filename": "15_empty_corrupted_doc.pdf",
        "text": """
Invoice #10293
Payment Receipt: $450.00
Thank you for your business.
""",
    },
]


async def main() -> None:
    """Execute complete database seeding."""
    print("=" * 70)
    print("RECRUIT LENS: SYNTHETIC DEMO DATA SEEDING")
    print("=" * 70)

    await init_db()

    async with AsyncSessionLocal() as db:
        # 1. Create or load Demo Tenant
        tenant_slug = "recruit-lens-labs"
        t_res = await db.execute(select(Tenant).where(Tenant.slug == tenant_slug))
        tenant = t_res.scalar_one_or_none()
        if not tenant:
            tenant = Tenant(
                name="Recruit Lens Labs",
                slug=tenant_slug,
                is_active=True,
            )
            db.add(tenant)
            await db.flush()
            print(f"Created demo tenant: {tenant.name} (ID: {tenant.id})")
        else:
            print(f"Using existing demo tenant: {tenant.name} (ID: {tenant.id})")

        # 2. Create or load Demo Recruiter User
        recruiter_email = "recruiter@recruitlens.local"
        u_res = await db.execute(select(User).where(User.email == recruiter_email))
        user = u_res.scalar_one_or_none()
        if not user:
            user = User(
                tenant_id=tenant.id,
                email=recruiter_email,
                hashed_password=hash_password("DemoRecruiter2026!"),
                full_name="Alex Mercer (Demo Recruiter)",
                role="admin",
                is_active=True,
            )
            db.add(user)
            await db.flush()
            print(f"Created demo recruiter account: {user.email}")
        else:
            print(f"Using existing demo recruiter account: {user.email}")

        # 3. Create realistic Job Requisitions
        taxonomy = SkillTaxonomy.get_instance()

        job1_raw = (
            "We are seeking a Senior Full-Stack Engineer to lead the architecture of our cloud web platforms. "
            "Requirements:\n"
            "- 5+ years of professional software engineering experience with Python and React.\n"
            "- Strong proficiency in FastAPI, asynchronous Python, and PostgreSQL.\n"
            "- Hands-on experience with Docker, microservices, and CI/CD pipelines.\n"
            "- Bachelor's degree in Computer Science or equivalent engineering field required.\n"
            "- Preferred: Experience with TypeScript, Redis, Kubernetes, or Tailwind CSS."
        )
        reqs1 = extract_job_requirements(
            jd_text=job1_raw,
            job_id="job_fullstack",
            title="Senior Full-Stack Engineer (Python / React)",
            taxonomy=taxonomy,
        )

        j1_res = await db.execute(
            select(Job).where(
                Job.tenant_id == tenant.id,
                Job.title == "Senior Full-Stack Engineer (Python / React)",
            )
        )
        job1 = j1_res.scalar_one_or_none()
        if not job1:
            job1 = Job(
                tenant_id=tenant.id,
                title="Senior Full-Stack Engineer (Python / React)",
                department="Engineering",
                raw_text=job1_raw,
                requirements_json=reqs1.model_dump(),
                weights_json={"skills": 0.5, "experience": 0.3, "education": 0.2},
                status="active",
            )
            db.add(job1)
            await db.flush()
            print(f"Created Job requisition 1: {job1.title}")

        job2_raw = (
            "We are hiring a Lead Data Scientist to build next-generation machine learning and NLP systems. "
            "Requirements:\n"
            "- 5+ years of production experience in machine learning and natural language processing.\n"
            "- Extensive hands-on experience with Python, PyTorch, Hugging Face transformers, and Scikit-Learn.\n"
            "- Experience deploying quantized ONNX or TensorRT models in production microservices.\n"
            "- Master's degree in Data Science, Computer Science, or Mathematics preferred.\n"
            "- Bonus: Experience with XGBoost, vector retrieval, and Docker."
        )
        reqs2 = extract_job_requirements(
            jd_text=job2_raw,
            job_id="job_datascience",
            title="Lead Data Scientist (Machine Learning & NLP)",
            taxonomy=taxonomy,
        )

        j2_res = await db.execute(
            select(Job).where(
                Job.tenant_id == tenant.id,
                Job.title == "Lead Data Scientist (Machine Learning & NLP)",
            )
        )
        job2 = j2_res.scalar_one_or_none()
        if not job2:
            job2 = Job(
                tenant_id=tenant.id,
                title="Lead Data Scientist (Machine Learning & NLP)",
                department="AI Research",
                raw_text=job2_raw,
                requirements_json=reqs2.model_dump(),
                weights_json={"skills": 0.55, "experience": 0.3, "education": 0.15},
                status="active",
            )
            db.add(job2)
            await db.flush()
            print(f"Created Job requisition 2: {job2.title}")

        # 4. Generate 15 Synthetic Resumes on disk and DB
        pdf_dir = settings.data_dir / "uploads" / tenant.id / job1.id
        pdf_dir.mkdir(parents=True, exist_ok=True)

        resumes_created: list[Resume] = []
        for cand in CANDIDATES:
            dest_file = pdf_dir / cand["filename"]
            create_pdf(dest_file, cand["text"])

            # Check if resume record exists
            r_res = await db.execute(
                select(Resume).where(
                    Resume.job_id == job1.id,
                    Resume.filename == cand["filename"],
                )
            )
            existing_r = r_res.scalar_one_or_none()
            if not existing_r:
                resume = Resume(
                    tenant_id=tenant.id,
                    job_id=job1.id,
                    filename=cand["filename"],
                    file_hash=f"seed_{cand['filename']}",
                    file_path=str(dest_file),
                    status="uploaded",
                )
                db.add(resume)
                resumes_created.append(resume)
            else:
                resumes_created.append(existing_r)

        await db.commit()
        print(f"Generated {len(CANDIDATES)} synthetic PDF resumes on disk.")

        # 5. Create background task tracker and execute ingestion
        task = BackgroundTask(
            tenant_id=tenant.id,
            job_id=job1.id,
            task_type="batch_ingestion",
            status="pending",
            progress=0,
            total=len(resumes_created),
            payload_json={"resume_count": len(resumes_created)},
            result_json={},
        )
        db.add(task)
        await db.commit()
        await db.refresh(task)
        task_id = task.id
        job_id = job1.id
        tenant_id = tenant.id

    print(f"\nTriggering batch ingestion worker task for {len(resumes_created)} resumes...")
    await process_batch_ingestion(task_id)

    # 6. Summary of results
    async with AsyncSessionLocal() as db:
        evals_res = await db.execute(
            select(Evaluation)
            .where(Evaluation.job_id == job_id, Evaluation.tenant_id == tenant_id)
            .order_by(Evaluation.total_score.desc())
        )
        evals = evals_res.scalars().all()

        print("\n" + "=" * 70)
        print("SEEDING SUMMARY: EVALUATIONS ACROSS TIERS")
        print("=" * 70)
        tier_counts: dict[str, int] = {}
        for ev in evals:
            tier_counts[ev.tier] = tier_counts.get(ev.tier, 0) + 1
            print(
                f"  Candidate: {ev.resume_id[:8]}... | Score: {ev.total_score:.4f} | Tier: {ev.tier:<12} | Decision: {ev.decision}"
            )

        print("\nTier Distribution:")
        for t_name, count in sorted(tier_counts.items()):
            print(f"  {t_name:<12}: {count} candidates")

    print("\nDEMO DATA SEEDING COMPLETE!")


if __name__ == "__main__":
    asyncio.run(main())
