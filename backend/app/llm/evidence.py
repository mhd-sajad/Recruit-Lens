"""
Evidence Packet compiler module.
Builds strictly bounded, verifiable evidence packets from parsed resumes and retrieval results.
"""

from app.core.features import CandidateFeatureVector
from app.core.jd_requirements import JobRequirements
from app.core.models import ResumeChunk, ResumeParseResult
from app.core.tiers import TierAssignmentResult
from app.llm.guardrails import detect_and_neutralize_injections, redact_pii_blind_mode
from app.llm.schemas import EvidenceChunk, EvidencePacket


def compile_evidence_packet(
    parsed_resume: ResumeParseResult,
    chunks: list[ResumeChunk],
    feature_vector: CandidateFeatureVector,
    tier_result: TierAssignmentResult,
    requirements: JobRequirements | None = None,
    top_k: int = 6,
) -> EvidencePacket:
    """
    Compile a bounded evidence packet for a candidate.
    Every chunk carries an explicit chunk_id (e.g. c_01), section, verbatim text, and offsets.
    """
    evidence_chunks: list[EvidenceChunk] = []
    has_injection = False

    raw_text = parsed_resume.raw_text

    # Take top-K most relevant chunks (or all if <= top_k)
    selected_chunks = chunks[:top_k]

    for idx, c in enumerate(selected_chunks, start=1):
        chunk_id = f"c_{idx:02d}"

        # Detect and neutralize any prompt injection text in the chunk
        sanitized_text, injection_flag = detect_and_neutralize_injections(c.text)
        if injection_flag:
            has_injection = True

        # Redact PII in blind mode
        blind_text = redact_pii_blind_mode(sanitized_text, parsed_resume.pii)

        # Locate character offsets in raw resume text if possible
        char_start = raw_text.find(c.text[:40]) if len(c.text) >= 40 else 0
        char_start = max(0, char_start)
        char_end = char_start + len(c.text)

        evidence_chunks.append(
            EvidenceChunk(
                chunk_id=chunk_id,
                resume_id=parsed_resume.resume_id,
                section=c.section.upper(),
                text=blind_text,
                char_start=char_start,
                char_end=char_end,
                metadata=c.metadata,
            )
        )

    # Degree strings
    req_degree = "None"
    if requirements and requirements.min_education_rank > 0:
        degree_map = {1: "Associate", 2: "Bachelor", 3: "Master", 4: "Doctorate"}
        req_degree = degree_map.get(requirements.min_education_rank, "Degree")

    cand_degree = "None"
    if parsed_resume.educations:
        cand_degree = parsed_resume.educations[0].degree or "Degree"

    cand_years = sum((exp.duration_months or 0) for exp in parsed_resume.experiences) / 12.0

    return EvidencePacket(
        candidate_id=parsed_resume.resume_id,
        job_id=requirements.job_id if requirements else None,
        retrieved_chunks=evidence_chunks,
        matched_must_skills=feature_vector.matched_must_skills,
        missing_must_skills=feature_vector.missing_must_skills,
        matched_nice_skills=feature_vector.matched_nice_skills,
        years_experience=round(cand_years, 1),
        required_years=round(requirements.min_years_experience if requirements else 0.0, 1),
        degree_level=cand_degree,
        required_degree=req_degree,
        assigned_tier=tier_result.tier,
        sanitized_blind_name="[Candidate]",
        injection_detected=has_injection,
    )
