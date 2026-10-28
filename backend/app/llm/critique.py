"""Self-RAG Critique module.

Performs strict sentence-level verification of generated claims against cited evidence chunks:
1. Entity, employer, and number extraction & matching.
2. Local ONNX embedding semantic similarity verification (calibrated at tau=0.65).
3. Automated multi-turn rewrite loop (up to 2 rewrites).
4. Strict safety BLOCK falling back to deterministic template if ungrounded.
"""

import re
from typing import Literal

import numpy as np

from app.core.embeddings import ONNXEmbedder
from app.llm.guardrails import SYSTEM_GUARDRAIL_PROMPT, format_evidence_block
from app.llm.provider import BaseLLMProvider
from app.llm.repair import parse_and_repair_json
from app.llm.schemas import (
    CandidateExplanation,
    CritiqueCheck,
    CritiqueResult,
    EvidenceChunk,
    EvidencePacket,
)
from app.llm.templates import generate_deterministic_explanation
from app.logging import get_logger

logger = get_logger("llm.critique")

CITATION_PATTERN = re.compile(r"\[(c_\d{2}(?:,\s*c_\d{2})*)\]")
NUMBER_PATTERN = re.compile(r"\$?\d+(?:,\d{3})*(?:\.\d+)?%?[kKmMbB]?", re.IGNORECASE)
EMPLOYER_PATTERN = re.compile(
    r"\b(?:at|for|from|by)\s+([A-Z][A-Za-z0-9]+(?:\s+[A-Z][A-Za-z0-9]+)?)\b"
)
TECH_PATTERN = re.compile(
    r"\b(Rust|Erlang|GitLab|ArgoCD|Flink|RabbitMQ|Vue|Elm|DynamoDB|Solidity|SvelteKit|SolidJS|Jax|DeepSpeed|Puppet|Chef|Datadog|Dynatrace|OpenStack|Tanzu|Azure|Bicep)\b",
    re.IGNORECASE,
)
METRIC_UNIT_PATTERN = re.compile(
    r"\b\d+\s*(?:gb|mb|tb|kb|%|ms|s|minutes|hours|days|years|yrs)\b", re.IGNORECASE
)

# Calibrated on 60 supported + 60 unsupported claims (docs/eval_critic_calibration.json)
# Achieving False Accept Rate <= 2.0% (measured: 1.67%)
CRITIQUE_SIMILARITY_THRESHOLD: float = 0.65


def extract_citations(text: str) -> list[str]:
    """Extract list of chunk IDs referenced in a string."""
    matches = CITATION_PATTERN.findall(text)
    cited_ids: list[str] = []
    for match in matches:
        ids = [chunk_id.strip() for chunk_id in match.split(",") if chunk_id.strip()]
        cited_ids.extend(ids)
    return list(dict.fromkeys(cited_ids))  # preserve order, unique


def verify_numbers_and_entities(sentence: str, chunk_text: str) -> tuple[bool, list[str]]:
    """Verify that numbers, dates, employer entities, and named technical tools exist in cited chunks."""
    sentence_clean = CITATION_PATTERN.sub("", sentence)
    missing: list[str] = []
    chunk_lower = chunk_text.lower()

    # 1. Standard numbers
    numbers = NUMBER_PATTERN.findall(sentence_clean)
    for num in numbers:
        num_clean = num.lower().replace(",", "")
        if num_clean not in chunk_lower and num_clean not in ("1", "2", "3", "4", "5", "10"):
            missing.append(f"Number/Metric: {num}")

    # 2. Metric units (e.g. 50 GB vs 500 MB)
    for m in METRIC_UNIT_PATTERN.findall(sentence_clean):
        if m.lower() not in chunk_lower:
            missing.append(f"MetricUnit: {m}")

    # 3. Employer / company mentions
    employers = EMPLOYER_PATTERN.findall(sentence_clean)
    for emp in employers:
        emp_clean = emp.lower().strip()
        if emp_clean in (
            "present",
            "scratch",
            "home",
            "remote",
            "least",
            "college",
            "school",
            "the",
        ):
            continue
        if emp_clean not in chunk_lower:
            missing.append(f"Entity/Employer: {emp}")

    # 4. Check specific technical keywords
    for tech in TECH_PATTERN.findall(sentence_clean):
        if tech.lower() not in chunk_lower:
            missing.append(f"TechSkill: {tech}")

    return (len(missing) == 0, missing)


_CRITIQUE_EMBEDDER: ONNXEmbedder | None = None


def get_critique_embedder() -> ONNXEmbedder:
    global _CRITIQUE_EMBEDDER
    if _CRITIQUE_EMBEDDER is None:
        _CRITIQUE_EMBEDDER = ONNXEmbedder(model_type="minilm")
    return _CRITIQUE_EMBEDDER


def compute_semantic_similarity(
    sentence: str, chunk_text: str, embedder: ONNXEmbedder | None = None
) -> float:
    """Compute cosine similarity between generated claim and cited chunk using ONNX embedder."""
    if not embedder:
        embedder = get_critique_embedder()

    sentence_clean = CITATION_PATTERN.sub("", sentence).strip()
    if not sentence_clean:
        return 1.0

    try:
        vecs = embedder.embed_texts([sentence_clean, chunk_text[:500]])
        v1, v2 = vecs[0], vecs[1]
        norm1 = float(np.linalg.norm(v1))
        norm2 = float(np.linalg.norm(v2))
        if norm1 > 0 and norm2 > 0:
            return float(np.dot(v1, v2) / (norm1 * norm2))
    except Exception as e:
        logger.warning(f"Embedding comparison error in critique: {e}")

    return 0.5


def check_explanation_sentences(
    explanation: CandidateExplanation,
    packet: EvidencePacket,
    embedder: ONNXEmbedder | None = None,
) -> list[CritiqueCheck]:
    """Verify grounding of each sentence in candidate explanation."""
    chunk_map: dict[str, EvidenceChunk] = {c.chunk_id: c for c in packet.retrieved_chunks}
    checks: list[CritiqueCheck] = []

    for idx, sentence in enumerate(explanation.sentences):
        cited_ids = extract_citations(sentence)
        if not cited_ids and idx < len(explanation.citations):
            cited_ids = explanation.citations[idx]

        # Case 1: Missing mandatory chunk citation
        if not cited_ids:
            checks.append(
                CritiqueCheck(
                    sentence_index=idx,
                    sentence=sentence,
                    cited_chunk_ids=[],
                    is_supported=False,
                    similarity_score=0.0,
                    failure_reason="Mandatory citation missing: every sentence must carry a supporting chunk tag [c_XX].",
                )
            )
            continue

        # Case 2: Citation provided but IDs invalid
        valid_chunks = [chunk_map[cid] for cid in cited_ids if cid in chunk_map]
        if not valid_chunks:
            checks.append(
                CritiqueCheck(
                    sentence_index=idx,
                    sentence=sentence,
                    cited_chunk_ids=cited_ids,
                    is_supported=False,
                    similarity_score=0.0,
                    failure_reason=f"Cited chunk ID(s) {cited_ids} do not exist in candidate evidence packet.",
                )
            )
            continue

        combined_chunk_text = " ".join(c.text for c in valid_chunks)

        # 1. Number and entity verification (strictly blocks false numbers even in tier statements)
        nums_ok, missing_items = verify_numbers_and_entities(sentence, combined_chunk_text)
        if not nums_ok:
            checks.append(
                CritiqueCheck(
                    sentence_index=idx,
                    sentence=sentence,
                    cited_chunk_ids=cited_ids,
                    is_supported=False,
                    similarity_score=0.0,
                    failure_reason=f"Unsupported numerical metrics, employers, or dates: {missing_items}",
                    unsupported_entities_or_numbers=missing_items,
                )
            )
            continue

        # 2. Semantic similarity verification
        sim = compute_semantic_similarity(sentence, combined_chunk_text, embedder)

        if sim < CRITIQUE_SIMILARITY_THRESHOLD:
            checks.append(
                CritiqueCheck(
                    sentence_index=idx,
                    sentence=sentence,
                    cited_chunk_ids=cited_ids,
                    is_supported=False,
                    similarity_score=sim,
                    failure_reason=f"Semantic similarity to cited evidence too low ({sim:.3f} < {CRITIQUE_SIMILARITY_THRESHOLD}). Possible hallucination.",
                )
            )
            continue

        checks.append(
            CritiqueCheck(
                sentence_index=idx,
                sentence=sentence,
                cited_chunk_ids=cited_ids,
                is_supported=True,
                similarity_score=sim,
                failure_reason=None,
            )
        )

    return checks


async def run_critique_and_refine(
    explanation: CandidateExplanation,
    packet: EvidencePacket,
    provider: BaseLLMProvider | None = None,
    max_rewrites: int = 2,
) -> tuple[CandidateExplanation, CritiqueResult]:
    """Run sentence-level critique with multi-turn rewrite loop (up to 2 rewrites) before BLOCK."""
    current_explanation = explanation
    rewrite_count = 0
    embedder = get_critique_embedder()

    for attempt in range(max_rewrites + 1):
        checks = check_explanation_sentences(current_explanation, packet, embedder)
        all_passed = all(c.is_supported for c in checks)

        if all_passed:
            verdict: Literal["PASS", "REWRITE", "BLOCK"] = (
                "REWRITE" if rewrite_count > 0 else "PASS"
            )
            result = CritiqueResult(
                verdict=verdict,
                checks=checks,
                rewrite_count=rewrite_count,
                rewritten_summary=current_explanation.summary_text if rewrite_count > 0 else None,
                is_fallback=False,
                critique_notes="All sentences grounded in cited evidence."
                if rewrite_count == 0
                else f"Passed grounded critique after {rewrite_count} rewrite(s).",
            )
            return current_explanation, result

        # If failures detected and rewrites remain
        if attempt < max_rewrites and provider is not None and provider.provider_name != "no_llm":
            rewrite_count += 1
            failures = [
                f"- Sentence {c.sentence_index + 1}: '{c.sentence}' -> {c.failure_reason}"
                for c in checks
                if not c.is_supported
            ]
            failures_text = "\n".join(failures)

            evidence_blocks = "\n\n".join(
                format_evidence_block(c.chunk_id, c.section, c.text)
                for c in packet.retrieved_chunks
            )

            rewrite_prompt = (
                f"Your previous explanation failed factual grounding critique on the following sentences:\n"
                f"{failures_text}\n\n"
                f"Candidate Evidence Packets:\n{evidence_blocks}\n\n"
                f"Instruction: Rewrite the candidate explanation so that 100% of statements are supported by "
                f"the evidence chunks above. Every sentence stating a skill, experience, or tier must cite its supporting chunk [c_XX]. "
                f"Do not mention unverified metrics or employers. Produce 3 to 4 concise sentences matching the schema."
            )

            try:
                resp = await provider.complete(
                    prompt=rewrite_prompt,
                    system_prompt=SYSTEM_GUARDRAIL_PROMPT,
                    json_mode=True,
                    max_tokens=1500,
                    temperature=0.1,
                )
                current_explanation = await parse_and_repair_json(
                    resp.content,
                    CandidateExplanation,
                    provider=provider,
                    system_prompt=SYSTEM_GUARDRAIL_PROMPT,
                    original_prompt=rewrite_prompt,
                )
                continue
            except Exception as e:
                logger.warning(f"Rewrite attempt {attempt + 1} failed: {e}")

    # Exhausted rewrites: hard safety BLOCK
    logger.warning("Explanation failed factual critique after rewrites. Triggering safety BLOCK.")
    deterministic_fallback = generate_deterministic_explanation(packet)
    fallback_checks = check_explanation_sentences(deterministic_fallback, packet, embedder)

    result = CritiqueResult(
        verdict="BLOCK",
        checks=fallback_checks,
        rewrite_count=rewrite_count,
        rewritten_summary=None,
        is_fallback=True,
        critique_notes=f"Candidate summary blocked after {rewrite_count} failed rewrite(s). Substituted deterministic template.",
    )
    return deterministic_fallback, result
