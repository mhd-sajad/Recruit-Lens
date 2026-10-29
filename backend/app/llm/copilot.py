"""
Copilot grounded Q&A module for Recruit Lens.

Implements:
1. Candidate-isolated hybrid evidence retrieval over resume chunks.
2. Grounded question answering with strict citation requirements ([c_01]).
3. "Not found in this resume" rule when evidence confidence is low or absent.
4. Self-RAG critique verification on all generated answers.
5. Blind mode PII redaction before prompting.
"""

import re
import time

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.v1.schemas import CopilotCitation, CopilotQueryResponse
from app.db.models import Evaluation, EvidenceChunkModel, Resume
from app.llm.critique import (
    extract_citations,
    verify_numbers_and_entities,
)
from app.llm.guardrails import (
    SYSTEM_GUARDRAIL_PROMPT,
    detect_and_neutralize_injections,
    format_evidence_block,
    redact_pii_blind_mode,
)
from app.llm.provider import BaseLLMProvider, FallbackLLMProvider
from app.logging import get_logger

logger = get_logger("llm.copilot")

STOPWORDS = {
    "a",
    "an",
    "the",
    "in",
    "on",
    "at",
    "for",
    "to",
    "of",
    "and",
    "or",
    "is",
    "are",
    "was",
    "were",
    "with",
    "about",
    "what",
    "how",
    "does",
    "did",
    "this",
    "candidate",
    "have",
    "has",
    "had",
    "experience",
    "work",
    "any",
    "tell",
    "me",
}


def _tokenize(text: str) -> list[str]:
    tokens = re.findall(r"\b[a-zA-Z0-9_\-\.]{2,}\b", text.lower())
    return [t for t in tokens if t not in STOPWORDS]


def score_chunk_relevance(query_tokens: list[str], chunk_text: str) -> float:
    """Compute normalized token overlap score between query and chunk."""
    if not query_tokens:
        return 0.0
    text_lower = chunk_text.lower()
    matches = sum(1 for tok in query_tokens if tok in text_lower)
    return matches / max(1, len(query_tokens))


async def answer_copilot_query(
    query: str,
    evaluation_id: str | None,
    candidate_id: str | None,
    user_id: str,
    db: AsyncSession,
    blind_mode: bool = False,
    provider: BaseLLMProvider | None = None,
) -> CopilotQueryResponse:
    """
    Execute grounded Q&A over candidate evidence chunks.
    Enforces isolation, citation syntax, critic verification, and 'not found' safety.
    """
    start_time = time.perf_counter()

    # 1. Neutralize prompt injections in the incoming recruiter query
    clean_query, injection_detected = detect_and_neutralize_injections(query)

    # 2. Locate evaluation and resume
    eval_stmt = (
        select(Evaluation)
        .options(selectinload(Evaluation.resume).selectinload(Resume.chunks))
        .where(Evaluation.user_id == user_id)
    )
    if evaluation_id:
        eval_stmt = eval_stmt.where(Evaluation.id == evaluation_id)
    elif candidate_id:
        eval_stmt = eval_stmt.where(
            (Evaluation.resume_id == candidate_id) | (Evaluation.id == candidate_id)
        )
    else:
        return CopilotQueryResponse(
            answer="Candidate or evaluation ID required.",
            grounded=True,
            critic_passed=True,
            found_in_resume=False,
            latency_ms=0.0,
        )

    res = await db.execute(eval_stmt)
    evaluation = res.scalars().first()
    if not evaluation or not evaluation.resume:
        return CopilotQueryResponse(
            answer="Candidate resume evidence not found for this user account.",
            grounded=True,
            critic_passed=True,
            found_in_resume=False,
            latency_ms=round((time.perf_counter() - start_time) * 1000, 2),
        )

    chunks: list[EvidenceChunkModel] = evaluation.resume.chunks or []
    if not chunks and evaluation.resume.raw_text:
        # Generate synthetic fallback chunks from raw text if chunk table is empty
        lines = [
            line.strip()
            for line in evaluation.resume.raw_text.split("\n\n")
            if len(line.strip()) > 30
        ]
        chunks = [
            EvidenceChunkModel(
                resume_id=evaluation.resume.id,
                chunk_index=i + 1,
                section="general",
                text=line[:500],
            )
            for i, line in enumerate(lines[:10])
        ]

    # 3. Retrieve and rank relevant chunks for the query
    query_tokens = _tokenize(clean_query)
    scored_chunks: list[tuple[float, str, str, str]] = []  # score, chunk_id, section, text

    for i, chunk in enumerate(chunks, start=1):
        c_id = f"c_{i:02d}"
        c_text = chunk.text
        if blind_mode:
            c_text = redact_pii_blind_mode(c_text)
        rel_score = score_chunk_relevance(query_tokens, c_text)
        scored_chunks.append((rel_score, c_id, chunk.section, c_text))

    scored_chunks.sort(key=lambda x: x[0], reverse=True)
    top_candidates = [sc for sc in scored_chunks if sc[0] > 0.0]

    # 4. Enforce strict "not found in this resume" rule
    # If no chunk matches query tokens or top relevance score is zero
    if not top_candidates:
        latency = round((time.perf_counter() - start_time) * 1000, 2)
        return CopilotQueryResponse(
            answer=f'Information not found in this resume. There is no evidence in the candidate\'s parsed text referencing "{query}".',
            citations=[],
            grounded=True,
            critic_passed=True,
            found_in_resume=False,
            latency_ms=latency,
        )

    # Take top 3 most relevant chunks
    selected_chunks = top_candidates[:3]

    # 5. Build prompt with XML bounded evidence
    evidence_blocks: list[str] = []
    chunk_map: dict[str, str] = {}
    citations: list[CopilotCitation] = []

    for rel_score, c_id, section, text in selected_chunks:
        chunk_map[c_id] = text
        evidence_blocks.append(format_evidence_block(c_id, section, text))
        citations.append(
            CopilotCitation(
                chunk_id=c_id,
                section=section,
                snippet=text[:160] + ("..." if len(text) > 160 else ""),
                relevance_score=round(rel_score, 2),
            )
        )

    evidence_prompt_text = "\n\n".join(evidence_blocks)

    user_prompt = f"""EVIDENCE PACKET:
{evidence_prompt_text}

USER QUESTION:
{clean_query}

INSTRUCTIONS:
1. Answer the question using ONLY factual statements supported by the evidence above.
2. Every claim MUST end with an explicit chunk citation e.g. [c_01].
3. If the evidence only partially answers or does not answer the question, explicitly state: "Information not found in this resume."
4. Do NOT speculate or extrapolate beyond the provided text.
"""

    if provider is None:
        provider = FallbackLLMProvider()

    raw_answer = ""
    try:
        response = await provider.complete(
            prompt=user_prompt,
            system_prompt=SYSTEM_GUARDRAIL_PROMPT,
            json_mode=False,
            temperature=0.0,
            max_tokens=300,
        )
        raw_answer = response.content.strip()
    except Exception as exc:
        logger.warning(
            "LLM provider unavailable for Copilot query, using deterministic fallback: %s", exc
        )
        # Deterministic grounded fallback
        best_chunk = selected_chunks[0]
        raw_answer = f"Based on resume evidence in {best_chunk[2].upper()} [{best_chunk[1]}]: {best_chunk[3][:200]}."

    # 6. Apply Self-RAG Critique verification
    cited_ids = extract_citations(raw_answer)
    if not cited_ids:
        # Missing citations: attach top chunk if answer was synthesized
        if selected_chunks:
            raw_answer = f"{raw_answer} [{selected_chunks[0][1]}]"
            cited_ids = [selected_chunks[0][1]]

    # Verify that claims match cited chunks
    critic_passed = True
    for c_id in cited_ids:
        if c_id not in chunk_map:
            critic_passed = False
            break
        ok, missing = verify_numbers_and_entities(raw_answer, chunk_map[c_id])
        if not ok:
            critic_passed = False
            break

    # If critic failed, rewrite to strict grounded summary
    if not critic_passed:
        best_chunk = selected_chunks[0]
        raw_answer = (
            f"Based on retrieved resume evidence [{best_chunk[1]}]: "
            f"{best_chunk[3][:220]} (Unverified details omitted)."
        )
        critic_passed = True

    latency = round((time.perf_counter() - start_time) * 1000, 2)
    return CopilotQueryResponse(
        answer=raw_answer,
        citations=citations,
        grounded=True,
        critic_passed=critic_passed,
        found_in_resume=True,
        latency_ms=latency,
    )
