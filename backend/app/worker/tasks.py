"""Resumable background worker tasks for resume ingestion, scoring, and selective LLM text generation."""

import hashlib
import logging

from sqlalchemy import select, update
from sqlalchemy.orm import selectinload

from app.config import settings
from app.core.embeddings import ONNXEmbedder
from app.core.features import extract_candidate_features
from app.core.jd_requirements import JobRequirements
from app.core.pdf_parser import parse_resume_pdf
from app.core.resume_chunker import chunk_resume
from app.core.scoring import WeightedBaselineScorer
from app.core.storage import get_storage_backend
from app.core.taxonomy import SkillTaxonomy
from app.core.tiers import assign_candidate_tier
from app.db.models import (
    BackgroundTask,
    EmailRecord,
    Evaluation,
    EvidenceChunkModel,
    Job,
    Resume,
    User,
)
from app.db.session import AsyncSessionLocal
from app.llm.agents.explainer import generate_candidate_explanation
from app.llm.agents.interviewer import generate_candidate_questions
from app.llm.provider import FallbackLLMProvider
from app.llm.schemas import EvidenceChunk, EvidencePacket
from app.llm.templates import (
    generate_deterministic_emails,
    generate_deterministic_explanation,
    generate_deterministic_questions,
)

logger = logging.getLogger(__name__)

# Shared taxonomy instance for worker tasks
_taxonomy: SkillTaxonomy | None = None
_embedder: ONNXEmbedder | None = None


def get_worker_taxonomy() -> SkillTaxonomy:
    """Lazily load and cache shared skills taxonomy."""
    global _taxonomy
    if _taxonomy is None:
        _taxonomy = SkillTaxonomy.get_instance()
    return _taxonomy


def get_worker_embedder() -> ONNXEmbedder:
    """Lazily load and cache shared CPU ONNX embedder."""
    global _embedder
    if _embedder is None:
        _embedder = ONNXEmbedder(model_type=settings.EMBEDDING_MODEL, quantized=True)
    return _embedder


def compute_evidence_hash(candidate_id: str, job_text: str, chunk_texts: list[str]) -> str:
    """Compute SHA-256 fingerprint over candidate evidence and job requirements."""
    content = f"{candidate_id}:{job_text}:" + ":".join(chunk_texts)
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


async def process_batch_ingestion(task_id: str) -> None:
    """Execute asynchronous, resumable batch parsing, hybrid retrieval, and deterministic scoring."""
    async with AsyncSessionLocal() as db:
        task_res = await db.execute(select(BackgroundTask).where(BackgroundTask.id == task_id))
        task = task_res.scalar_one_or_none()
        if task is None:
            logger.error(f"Worker task {task_id} not found in database")
            return

        if task.status in ("completed", "cancelled"):
            return

        task.status = "processing"
        await db.commit()

        user_id = task.user_id
        job_id = task.payload_json.get("job_id")

        job_res = await db.execute(select(Job).where(Job.id == job_id, Job.user_id == user_id))
        job = job_res.scalar_one_or_none()
        if job is None:
            task.status = "failed"
            task.error_message = f"Job {job_id} not found"
            await db.commit()
            return

        try:
            reqs_data = job.requirements_json
            job_reqs = (
                JobRequirements(**reqs_data)
                if reqs_data
                else JobRequirements(
                    job_id=job.id,
                    title=job.title,
                    must_have_skills=[],
                    nice_to_have_skills=[],
                )
            )
        except Exception as e:
            logger.warning(f"Failed to parse job requirements: {e}. Building minimal fallback.")
            job_reqs = JobRequirements(
                job_id=job.id,
                title=job.title,
                must_have_skills=[],
                nice_to_have_skills=[],
            )

        # Load all resumes for this job
        resumes_res = await db.execute(
            select(Resume)
            .where(Resume.job_id == job.id, Resume.user_id == user_id)
            .order_by(Resume.created_at.asc())
        )
        resumes = resumes_res.scalars().all()
        task.total = len(resumes)
        await db.commit()

    taxonomy = get_worker_taxonomy()
    get_worker_embedder()  # Warm up shared ONNX embedder in worker process
    scorer = WeightedBaselineScorer(weights=job.weights_json)
    storage = get_storage_backend()

    # Process each resume idempotently (resumability)
    for idx, resume in enumerate(resumes, start=1):
        # Check task cancellation
        async with AsyncSessionLocal() as db:
            task_check = await db.execute(
                select(BackgroundTask).where(BackgroundTask.id == task_id)
            )
            t = task_check.scalar_one_or_none()
            if t and t.status == "cancelled":
                logger.info(f"Task {task_id} was cancelled by user. Halting batch ingestion.")
                return

        # Check if already processed
        async with AsyncSessionLocal() as db:
            eval_check = await db.execute(
                select(Evaluation).where(
                    Evaluation.resume_id == resume.id, Evaluation.user_id == user_id
                )
            )
            if eval_check.scalar_one_or_none() is not None:
                # Update progress
                await db.execute(
                    update(BackgroundTask).where(BackgroundTask.id == task_id).values(progress=idx)
                )
                await db.commit()
                continue

        try:
            # 1. Retrieve PDF bytes from storage abstraction
            pdf_bytes = await storage.get_file(resume.storage_path)

            # Write to a temporary file for pdf_parser
            temp_pdf_path = settings.data_dir / "temp" / f"{resume.id}.pdf"
            temp_pdf_path.parent.mkdir(parents=True, exist_ok=True)
            temp_pdf_path.write_bytes(pdf_bytes)

            try:
                # 2. Parse PDF
                pdf_result = parse_resume_pdf(temp_pdf_path)
            finally:
                if temp_pdf_path.exists():
                    temp_pdf_path.unlink()

            # 3. Resume Chunking
            chunks = chunk_resume(pdf_result)

            # 4. Feature Extraction & Scoring
            features = extract_candidate_features(
                parsed_resume=pdf_result,
                job_reqs=job_reqs,
                taxonomy=taxonomy,
            )
            scored = scorer.score(features)

            # 5. Assign Fit Tier
            tier_res = assign_candidate_tier(
                score_result=scored,
                feature_vector=features,
                parse_confidence=pdf_result.parse_confidence,
                is_verified_resume=pdf_result.is_resume,
            )
            assigned_tier = tier_res.tier

            # 6. Convert chunks to evidence chunks
            evidence_chunks = [
                EvidenceChunk(
                    chunk_id=f"c_{i + 1:02d}",
                    resume_id=resume.id,
                    section=c.section,
                    text=c.text,
                )
                for i, c in enumerate(chunks[:10])
            ]

            # 7. Deterministic Zero-Wait Templates (Marked as "template")
            ev_packet = EvidencePacket(
                candidate_id=resume.id,
                job_id=job.id,
                retrieved_chunks=evidence_chunks,
                matched_must_skills=features.matched_must_skills,
                missing_must_skills=features.missing_must_skills,
                matched_nice_skills=features.matched_nice_skills,
                years_experience=features.years_gap.value + job_reqs.min_years_experience,
                required_years=job_reqs.min_years_experience,
                degree_level=(
                    pdf_result.educations[0].degree
                    if pdf_result.educations and pdf_result.educations[0].degree
                    else "Unknown"
                ),
                required_degree=job_reqs.min_education_name or "Unknown",
                assigned_tier=assigned_tier,
            )

            det_explanation = generate_deterministic_explanation(ev_packet)
            det_questions = generate_deterministic_questions(ev_packet)
            det_emails = generate_deterministic_emails(ev_packet)

            ev_hash = compute_evidence_hash(
                resume.id, job.raw_text, [c.text for c in evidence_chunks]
            )

            # 8. Persist evaluation and chunks
            async with AsyncSessionLocal() as db:
                evaluation = Evaluation(
                    user_id=user_id,
                    job_id=job.id,
                    resume_id=resume.id,
                    total_score=scored.final_score,
                    tier=assigned_tier,
                    confidence=pdf_result.gate_confidence,
                    stage="screened",
                    breakdown_json={
                        "skills": {
                            "score": features.must_have_coverage.value,
                            "matched_must": features.matched_must_skills,
                            "missing_must": features.missing_must_skills,
                            "matched_nice": features.matched_nice_skills,
                        },
                        "experience": {
                            "score": max(0.0, 1.0 - max(0.0, -features.years_gap.value) / 5.0),
                            "years": features.years_gap.value + job_reqs.min_years_experience,
                            "required_years": job_reqs.min_years_experience,
                        },
                        "education": {
                            "score": 1.0 if features.education_match.value >= 0 else 0.5,
                            "degree": pdf_result.educations[0].degree
                            if pdf_result.educations
                            else "Not Specified",
                        },
                        "semantic": {"score": features.dense_similarity.value},
                    },
                    explanation_json=det_explanation.model_dump(),
                    explanation_type="template",
                    interview_questions_json=det_questions.model_dump(),
                    email_drafts_json=det_emails.model_dump(),
                    evidence_hash=ev_hash,
                    llm_generated=False,
                )
                db.add(evaluation)
                await db.flush()

                # Add draft email records
                email_records = [
                    EmailRecord(
                        user_id=user_id,
                        evaluation_id=evaluation.id,
                        email_type="interview_invitation",
                        recipient_email=f"candidate_{resume.id[:8]}@example.com",
                        subject=det_emails.invite.subject,
                        body=det_emails.invite.body,
                        status="draft",
                    ),
                    EmailRecord(
                        user_id=user_id,
                        evaluation_id=evaluation.id,
                        email_type="rejection",
                        recipient_email=f"candidate_{resume.id[:8]}@example.com",
                        subject=det_emails.rejection.subject,
                        body=det_emails.rejection.body,
                        status="draft",
                    ),
                    EmailRecord(
                        user_id=user_id,
                        evaluation_id=evaluation.id,
                        email_type="hold_update",
                        recipient_email=f"candidate_{resume.id[:8]}@example.com",
                        subject=det_emails.hold.subject,
                        body=det_emails.hold.body,
                        status="draft",
                    ),
                ]
                db.add_all(email_records)

                # Persist evidence chunks
                for i, c in enumerate(chunks):
                    chunk_model = EvidenceChunkModel(
                        resume_id=resume.id,
                        chunk_index=i,
                        section=c.section,
                        text=c.text,
                        char_start=0,
                        char_end=len(c.text),
                        metadata_json=c.metadata,
                    )
                    db.add(chunk_model)

                # Update resume status
                resume_db = await db.get(Resume, resume.id)
                if resume_db:
                    resume_db.status = "parsed"
                    resume_db.raw_text = pdf_result.raw_text

                # Update task progress
                task_db = await db.get(BackgroundTask, task_id)
                if task_db:
                    task_db.progress = idx

                await db.commit()

        except Exception as e:
            logger.error(f"Error processing resume {resume.id}: {e}", exc_info=True)
            async with AsyncSessionLocal() as db:
                resume_db = await db.get(Resume, resume.id)
                if resume_db:
                    resume_db.status = "error"
                task_db = await db.get(BackgroundTask, task_id)
                if task_db:
                    task_db.progress = idx
                await db.commit()

    # Mark task completed
    async with AsyncSessionLocal() as db:
        final_task = await db.get(BackgroundTask, task_id)
        if final_task and final_task.status != "cancelled":
            final_task.status = "completed"
            final_task.result_json = {"processed": len(resumes), "job_id": job.id}
            await db.commit()


async def generate_on_demand_llm_text(evaluation_id: str, user_id: str | None = None) -> bool:
    """Execute LLM text generation with evidence hash caching."""
    async with AsyncSessionLocal() as db:
        query = (
            select(Evaluation)
            .options(selectinload(Evaluation.resume))
            .where(Evaluation.id == evaluation_id)
        )
        if user_id:
            query = query.where(Evaluation.user_id == user_id)
        ev_res = await db.execute(query)
        evaluation = ev_res.scalar_one_or_none()
        if evaluation is None:
            return False

        # Load chunks
        chunks_res = await db.execute(
            select(EvidenceChunkModel)
            .where(EvidenceChunkModel.resume_id == evaluation.resume_id)
            .order_by(EvidenceChunkModel.chunk_index.asc())
        )
        chunks = chunks_res.scalars().all()

        retrieved_chunks = [
            EvidenceChunk(
                chunk_id=f"c_{c.chunk_index + 1:02d}",
                resume_id=c.resume_id,
                section=c.section,
                text=c.text,
            )
            for c in chunks[:10]
        ]

        # Load Job
        job_res = await db.execute(select(Job).where(Job.id == evaluation.job_id))
        job = job_res.scalar_one_or_none()

        # Reconstruct packet
        breakdown = evaluation.breakdown_json
        ev_packet = EvidencePacket(
            candidate_id=evaluation.resume_id,
            job_id=evaluation.job_id,
            retrieved_chunks=retrieved_chunks,
            matched_must_skills=breakdown.get("skills", {}).get("matched_must", []),
            missing_must_skills=breakdown.get("skills", {}).get("missing_must", []),
            matched_nice_skills=breakdown.get("skills", {}).get("matched_nice", []),
            years_experience=float(breakdown.get("experience", {}).get("years", 0.0)),
            required_years=float(breakdown.get("experience", {}).get("required_years", 0.0)),
            degree_level=str(breakdown.get("education", {}).get("degree", "Unknown")),
            required_degree=(
                job.requirements_json.get("min_education_name", "Bachelor's")
                if job and job.requirements_json
                else "Bachelor's"
            ),
            assigned_tier=evaluation.tier,
        )

        provider = FallbackLLMProvider()

        # Generate synthesized explanation and interview questions
        expl, _, p_toks_e, c_toks_e = await generate_candidate_explanation(ev_packet, provider)
        questions, _, p_toks_q, c_toks_q = await generate_candidate_questions(ev_packet, provider)

        # Update evaluation
        evaluation.explanation_json = expl.model_dump()
        evaluation.explanation_type = "llm"
        evaluation.interview_questions_json = questions.model_dump()
        evaluation.llm_generated = True

        # Track token usage on User
        total_tokens = p_toks_e + c_toks_e + p_toks_q + c_toks_q
        user = await db.get(User, evaluation.user_id)
        if user:
            user.daily_token_usage += total_tokens

        await db.commit()
        return True
