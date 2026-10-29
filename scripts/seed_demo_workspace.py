#!/usr/bin/env python3
"""
Seed script for Recruit Lens Demo Workspace.

Creates:
1. Demo Recruiter Admin Account (admin@recruitlens.local / Admin123!)
2. Realistic active Job Requisitions with extracted requirements
3. Synthetic candidate evaluations across tiers (FastTrack, Review, Hold, Reject)
4. Grounded evidence chunks and interview scorecards
Strictly synthetic data: zero candidate PII and zero real resumes.
"""

import asyncio
from datetime import UTC, datetime
from pathlib import Path
import sys

# Add backend to path
backend_path = Path(__file__).resolve().parent.parent / "backend"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

from app.auth.security import hash_password
from app.db.base import Base
from app.db.models import (
    Evaluation,
    EvidenceChunkModel,
    Job,
    Resume,
    User,
)
from app.db.session import AsyncSessionLocal, engine


async def seed() -> None:
    print("==> Initializing Recruit Lens Demo Workspace...")

    # Ensure tables exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        # 1. Create or retrieve demo admin user
        admin_email = "admin@recruitlens.local"
        user = User(
            email=admin_email,
            hashed_password=hash_password("Admin123!"),
            full_name="Lead Recruiter (Demo)",
            role="admin",
            api_key="lens_demo_api_key_for_mcp_evaluation_12345",  # gitleaks:allow
        )
        session.add(user)
        await session.flush()
        print(f"  [+] Created Demo User: {admin_email} / Admin123!")

        # 2. Create Requisition 1: Staff Backend Engineer
        job1 = Job(
            user_id=user.id,
            title="Staff Backend Engineer - Distributed Systems",
            department="Core Infrastructure",
            status="active",
            raw_text="""We are seeking a Staff Backend Engineer to design high-throughput distributed systems.
Must-have qualifications:
- 6+ years experience with Python or Go
- Deep knowledge of PostgreSQL, Redis, and message streaming (Kafka or RabbitMQ)
- Experience designing resilient microservices and gRPC APIs
- Docker, Kubernetes, and AWS infrastructure experience
Nice-to-have:
- Rust or Erlang experience
- Open source contributions
Education: Bachelor's degree in Computer Science or related field.""",
            requirements_json={
                "must_have_skills": ["python", "postgresql", "redis", "kafka", "docker", "aws"],
                "nice_to_have_skills": ["go", "kubernetes", "grpc", "rust"],
                "min_years_experience": 6,
                "education_level": "bachelor",
            },
            weights_json={"skills": 0.40, "experience": 0.30, "education": 0.15, "semantic": 0.15},
        )
        session.add(job1)

        # Create Requisition 2: Senior Machine Learning Engineer
        job2 = Job(
            user_id=user.id,
            title="Senior Machine Learning Engineer - Search & NLP",
            department="AI Research & Search",
            status="active",
            raw_text="""Seeking an ML Engineer to scale vector search, hybrid retrieval, and LLM inference.
Must-have:
- 5+ years experience in Applied Machine Learning
- Strong proficiency in PyTorch, Python, and Hugging Face Transformers
- Experience with dense embeddings, BM25, and semantic reranking
- Experience deploying ONNX Runtime or TensorRT in production
Nice-to-have:
- Vector databases (Qdrant, Milvus, or Pinecone)
- LLM fine-tuning (LoRA, QLoRA)
Education: Master's or PhD preferred.""",
            requirements_json={
                "must_have_skills": ["python", "pytorch", "transformers", "onnx", "embeddings"],
                "nice_to_have_skills": ["vector search", "tensorrt", "docker", "nlp"],
                "min_years_experience": 5,
                "education_level": "master",
            },
            weights_json={"skills": 0.45, "experience": 0.25, "education": 0.15, "semantic": 0.15},
        )
        session.add(job2)
        await session.flush()
        print(f"  [+] Created Active Requisitions: '{job1.title}' & '{job2.title}'")

        # 3. Create synthetic candidates for Job 1
        candidates_data = [
            {
                "filename": "Alex_Vance_Staff_Backend.pdf",
                "tier": "FastTrack",
                "score": 93.4,
                "stage": "interview_scheduled",
                "summary": "Exceeds all core criteria with 8 years building distributed microservices in Python, Kafka, and PostgreSQL. Demonstrates strong architectural leadership.",
                "chunks": [
                    ("skills", "Core proficiencies: Python, PostgreSQL, Kafka, Redis, Docker, AWS, Go, Kubernetes, gRPC."),
                    ("experience", "Staff Infrastructure Engineer at ScaleFlow (2020 - Present): Architected event-driven data pipeline handling 45k msgs/sec using Kafka and PostgreSQL. Reduced latency by 42%."),
                    ("education", "B.S. in Computer Science, University of Michigan (2016)."),
                ],
            },
            {
                "filename": "Morgan_Chen_Senior_Dev.pdf",
                "tier": "Review",
                "score": 81.2,
                "stage": "shortlisted",
                "summary": "Strong backend background with 5.5 years in Python and Docker. Slightly under the 6-year target but strong technical signals.",
                "chunks": [
                    ("skills", "Proficiencies: Python, Django, FastAPI, PostgreSQL, Docker, AWS, Redis."),
                    ("experience", "Senior Backend Developer at CloudPulse (2019 - Present): Developed high-availability REST and gRPC microservices backed by PostgreSQL."),
                    ("education", "B.S. in Information Systems (2019)."),
                ],
            },
            {
                "filename": "Jordan_Taylor_Mid_Backend.pdf",
                "tier": "Hold",
                "score": 67.8,
                "stage": "screened",
                "summary": "Solid software development foundation (3 years), but missing required senior distributed systems experience and message streaming.",
                "chunks": [
                    ("skills", "Python, Flask, SQLite, Docker, Git, Linux."),
                    ("experience", "Software Developer at DevAgency (2021 - Present): Built web backends and internal dashboards using Python Flask and Docker."),
                    ("education", "B.A. in Computer Science (2021)."),
                ],
            },
            {
                "filename": "Taylor_Reese_Frontend_Specialist.pdf",
                "tier": "Reject",
                "score": 42.1,
                "stage": "screened",
                "summary": "Specialized in React, Vue, and CSS. Missing must-have requirements: distributed backend architectures, Kafka, and database internals.",
                "chunks": [
                    ("skills", "JavaScript, TypeScript, React, Next.js, Tailwind CSS, HTML5, Jest."),
                    ("experience", "Senior Frontend Engineer (2018 - Present): Built interactive user interfaces and component libraries in React."),
                    ("education", "B.S. in Graphic & Interactive Design (2018)."),
                ],
            },
        ]

        for cand in candidates_data:
            resume = Resume(
                user_id=user.id,
                job_id=job1.id,
                filename=cand["filename"],
                storage_path=f"/demo/{cand['filename']}",
                file_hash=f"hash_{hash(cand['filename'])}",
                raw_text="\n\n".join(chunk[1] for chunk in cand["chunks"]),
            )
            session.add(resume)
            await session.flush()

            for idx, (section, text) in enumerate(cand["chunks"], start=1):
                chunk_record = EvidenceChunkModel(
                    resume_id=resume.id,
                    chunk_index=idx,
                    section=section,
                    text=text,
                )
                session.add(chunk_record)

            evaluation = Evaluation(
                user_id=user.id,
                job_id=job1.id,
                resume_id=resume.id,
                total_score=cand["score"],
                tier=cand["tier"],
                stage=cand["stage"],
                confidence=1.0,
                evidence_hash=f"evhash_{resume.id}",
                breakdown_json={
                    "skills": {"score": cand["score"] / 100.0, "weight": 0.40},
                    "experience": {"score": cand["score"] / 100.0, "weight": 0.30},
                    "education": {"score": 0.90, "weight": 0.15},
                    "semantic": {"score": cand["score"] / 100.0, "weight": 0.15},
                },
                explanation_json={
                    "summary": cand["summary"],
                    "strengths": ["Demonstrated proficiency in core requirements", "Clear evidence alignment"],
                    "gaps": [] if cand["tier"] == "FastTrack" else ["Years of experience or specific streaming tools"],
                },
                explanation_type="template",
                interview_questions_json={
                    "questions": [
                        {
                            "question": "Can you walk us through your architecture for distributed stream processing?",
                            "rationale": "Evaluates candidate experience with Kafka and message reliability.",
                            "evidence_citation": "[c_02]",
                        }
                    ]
                },
                email_drafts_json={
                    "interview_invitation": {
                        "subject": "Interview Invitation: Staff Backend Engineer at Recruit Lens",
                        "body": "Hi there,\n\nOur recruiting team was impressed by your distributed systems background and would love to schedule a technical conversation.",
                    }
                },
            )
            session.add(evaluation)

        await session.commit()
        print(f"  [+] Seeded {len(candidates_data)} evaluated candidates across all tiers.")
        print("==> Demo Workspace setup COMPLETE!")


if __name__ == "__main__":
    asyncio.run(seed())
