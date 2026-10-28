"""Resumable background worker tasks for resume ingestion, scoring, and LLM text generation."""

import hashlib
import logging
from pathlib import Path

from sqlalchemy import select

from app.core.embeddings import ONNXEmbedder
from app.core.features import extract_candidate_features
from app.core.jd_requirements import JobRequirements
from app.core.pdf_parser import parse_resume_pdf
from app.core.resume_chunker import chunk_resume
from app.core.scoring import WeightedBaselineScorer
from app.core.taxonomy import SkillTaxonomy
from app.core.tiers import assign_candidate_tier
from app.db.models import BackgroundTask, Evaluation, EvidenceChunkModel, Job, Resume
from app.db.session import AsyncSessionLocal
from app.llm.agents.explainer import generate_candidate_explanation
from app.llm.agents.interviewer import generate_candidate_questions
from app.llm.provider import FallbackLLMProvider, GroqProvider, NoLLMProvider
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
        _embedder = ONNXEmbedder(model_type="minilm", quantized=True)
    return _embedder


def compute_evidence_hash(candidate_id: str, job_text: str, chunk_texts: list[str]) -> str:
    """Compute SHA-256 fingerprint over candidate evidence and job requirements."""
    content = f"{candidate_id}:{job_text}:" + ":".join(chunk_texts)
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


async def process_batch_ingestion(task_id: str) -> None:
    """
    Execute asynchronous, resumable batch parsing, hybrid retrieval, and scoring.

    If interrupted, resumes from the first unscored candidate without duplicate processing.
    """
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(BackgroundTask).where(BackgroundTask.id == task_id))
        task = result.scalar_one_or_none()
        if not task:
            logger.error(f"Task {task_id} not found in database")
            return

        task.status = "processing"
        await db.commit()

        tenant_id = task.tenant_id
        job_id = task.job_id
        if not job_id:
            task.status = "failed"
            task.error_message = "Task missing associated job_id"
            await db.commit()
            return

        # Load Job
        job_res = await db.execute(select(Job).where(Job.id == job_id, Job.tenant_id == tenant_id))
        job = job_res.scalar_one_or_none()
        if not job:
            task.status = "failed"
            task.error_message = f"Job {job_id} not found"
            await db.commit()
            return

        # Parse job requirements model
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
            select(Resume).where(Resume.job_id == job_id, Resume.tenant_id == tenant_id)
        )
        resumes = resumes_res.scalars().all()
        task.total = len(resumes)
        await db.commit()

        taxonomy = get_worker_taxonomy()
        embedder = get_worker_embedder()
        scorer = WeightedBaselineScorer(weights=job.weights_json or None)
        processed_count = 0

        for resume in resumes:
            try:
                # 1. Check if evaluation already exists (resumability)
                eval_res = await db.execute(
                    select(Evaluation).where(
                        Evaluation.resume_id == resume.id,
                        Evaluation.tenant_id == tenant_id,
                    )
                )
                existing_eval = eval_res.scalar_one_or_none()
                if existing_eval:
                    processed_count += 1
                    task.progress = processed_count
                    await db.commit()
                    continue

                # 2. Extract and parse PDF text if not parsed
                pdf_path = Path(resume.file_path)
                if not pdf_path.exists():
                    logger.warning(f"Resume file not found on disk: {pdf_path}")
                    resume.status = "failed"
                    processed_count += 1
                    task.progress = processed_count
                    await db.commit()
                    continue

                pdf_result = parse_resume_pdf(pdf_path, resume_id=resume.id)
                raw_text = pdf_result.raw_text
                resume.parsed_data_json = {
                    "text": raw_text[:20000],
                    "confidence": pdf_result.parse_confidence,
                    "page_count": pdf_result.page_count,
                    "is_resume": pdf_result.is_resume,
                }
                resume.status = "parsed"
                await db.commit()

                # 3. Chunk resume and save evidence chunks
                chunks = chunk_resume(pdf_result)
                chunk_texts = [c.text for c in chunks]

                # Compute chunk embeddings in batch
                chunk_embeddings = embedder.embed_texts(chunk_texts, batch_size=32)

                for c_idx, c_obj in enumerate(chunks):
                    emb_bytes = chunk_embeddings[c_idx].tobytes()
                    db_chunk = EvidenceChunkModel(
                        tenant_id=tenant_id,
                        resume_id=resume.id,
                        chunk_index=c_idx,
                        section=c_obj.section,
                        text=c_obj.text,
                        embedding_bytes=emb_bytes,
                    )
                    db.add(db_chunk)
                await db.commit()

                # 4. Extract feature vector and compute score
                features = extract_candidate_features(
                    parsed_resume=pdf_result,
                    job_reqs=job_reqs,
                    taxonomy=taxonomy,
                )

                score_result = scorer.score(features)
                total_score = score_result.final_score

                # 5. Assign calibrated tier
                tier_result = assign_candidate_tier(
                    score_result=score_result,
                    feature_vector=features,
                    parse_confidence=pdf_result.parse_confidence,
                    is_verified_resume=pdf_result.is_resume,
                )
                assigned_tier = tier_result.tier

                # 6. Build evidence chunks for packet
                evidence_chunks = [
                    EvidenceChunk(
                        chunk_id=f"c_{i + 1:02d}",
                        resume_id=resume.id,
                        section=c.section,
                        text=c.text,
                    )
                    for i, c in enumerate(chunks[:10])
                ]

                # 7. Deterministic zero-wait templates
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

                # 8. Persist Evaluation
                evaluation = Evaluation(
                    tenant_id=tenant_id,
                    job_id=job.id,
                    resume_id=resume.id,
                    total_score=round(total_score, 4),
                    tier=assigned_tier,
                    confidence=round(pdf_result.parse_confidence, 4),
                    breakdown_json={
                        "score_breakdown": score_result.model_dump(),
                        "matched_must_skills": features.matched_must_skills,
                        "missing_must_skills": features.missing_must_skills,
                        "matched_nice_skills": features.matched_nice_skills,
                        "years_experience": features.years_gap.value
                        + job_reqs.min_years_experience,
                        "required_experience_years": job_reqs.min_years_experience,
                        "highest_education": pdf_result.educations[0].degree
                        if pdf_result.educations
                        else "Not Specified",
                    },
                    explanation_json=det_explanation.model_dump(),
                    questions_json=det_questions.model_dump(),
                    email_drafts_json=det_emails.model_dump(),
                    evidence_hash=ev_hash,
                    llm_generated=False,
                )
                db.add(evaluation)
                resume.status = "scored"
                await db.commit()

            except Exception as item_err:
                logger.error(f"Error processing resume {resume.id}: {item_err}", exc_info=True)
                resume.status = "failed"
                await db.commit()

            processed_count += 1
            task.progress = processed_count
            await db.commit()

        task.status = "completed"
        task.result_json = {"total_processed": processed_count, "total_resumes": len(resumes)}
        await db.commit()


async def generate_on_demand_llm_text(evaluation_id: str, tenant_id: str) -> bool:
    """
    Generate or retrieve cached LLM explanation, interview questions, and email drafts.

    Grounded strictly in retrieved resume evidence chunks with Self-RAG verification.
    """
    async with AsyncSessionLocal() as db:
        eval_res = await db.execute(
            select(Evaluation).where(
                Evaluation.id == evaluation_id, Evaluation.tenant_id == tenant_id
            )
        )
        evaluation = eval_res.scalar_one_or_none()
        if not evaluation:
            return False

        # Load resume chunks
        chunks_res = await db.execute(
            select(EvidenceChunkModel).where(
                EvidenceChunkModel.resume_id == evaluation.resume_id,
                EvidenceChunkModel.tenant_id == tenant_id,
            )
        )
        db_chunks = chunks_res.scalars().all()
        retrieved_chunks = [
            EvidenceChunk(
                chunk_id=f"c_{c.chunk_index + 1:02d}",
                resume_id=c.resume_id,
                section=c.section,
                text=c.text,
            )
            for c in db_chunks[:10]
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
            matched_must_skills=breakdown.get("matched_must_skills", []),
            missing_must_skills=breakdown.get("missing_must_skills", []),
            matched_nice_skills=breakdown.get("matched_nice_skills", []),
            years_experience=float(breakdown.get("years_experience", 0.0)),
            required_years=float(breakdown.get("required_experience_years", 0.0)),
            degree_level=str(breakdown.get("highest_education", "Unknown")),
            required_degree=(
                job.requirements_json.get("min_education_name", "Bachelor's")
                if job and job.requirements_json
                else "Bachelor's"
            ),
            assigned_tier=evaluation.tier,
        )

        provider = FallbackLLMProvider(
            providers=[
                GroqProvider(model="openai/gpt-oss-120b"),
                NoLLMProvider(),
            ]
        )

        # Generate explanation
        exp, _, _, _ = await generate_candidate_explanation(ev_packet, provider)
        questions, _, _, _ = await generate_candidate_questions(ev_packet, provider)
        emails = generate_deterministic_emails(ev_packet)

        evaluation.explanation_json = exp.model_dump()
        evaluation.questions_json = questions.model_dump()
        evaluation.email_drafts_json = emails.model_dump()
        evaluation.llm_generated = True
        await db.commit()
        return True
