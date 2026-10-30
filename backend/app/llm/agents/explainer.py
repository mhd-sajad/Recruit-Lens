"""
Candidate Explainer Agent.
Generates concise, 3 to 4 sentence evidence-grounded candidate evaluations with explicit chunk citations.
"""

from app.llm.guardrails import SYSTEM_GUARDRAIL_PROMPT, format_evidence_block
from app.llm.provider import BaseLLMProvider
from app.llm.repair import parse_and_repair_json
from app.llm.schemas import CandidateExplanation, EvidencePacket
from app.llm.templates import generate_deterministic_explanation
from app.logging import get_logger

logger = get_logger("agents.explainer")


async def generate_candidate_explanation(
    packet: EvidencePacket,
    provider: BaseLLMProvider,
) -> tuple[CandidateExplanation, bool, int, int]:
    """
    Generate structured candidate explanation citing retrieved chunks.
    Returns: (CandidateExplanation, is_fallback, prompt_tokens, completion_tokens)
    """
    if provider.provider_name == "no_llm":
        return generate_deterministic_explanation(packet), True, 0, 0

    evidence_str = "\n\n".join(
        format_evidence_block(c.chunk_id, c.section, c.text) for c in packet.retrieved_chunks
    )

    matched_skills_str = (
        ", ".join(packet.matched_must_skills) if packet.matched_must_skills else "None"
    )
    missing_skills_str = (
        ", ".join(packet.missing_must_skills) if packet.missing_must_skills else "None"
    )

    if packet.years_experience is not None:
        exp_line = f"Experience: {packet.years_experience:.1f} years (Required: {packet.required_years:.1f} years)"
    else:
        exp_line = f"Experience: UNKNOWN (dates unverified in resume) (Required: {packet.required_years:.1f} years)"

    prompt = f"""EVALUATION TASK:
Candidate ID: {packet.candidate_id}
Assigned Tier: {packet.assigned_tier}
{exp_line}
Education: {packet.degree_level} (Required: {packet.required_degree})
Matched Mandatory Skills: {matched_skills_str}
Missing Mandatory Skills: {missing_skills_str}

CANDIDATE EVIDENCE CHUNKS:
{evidence_str}

INSTRUCTIONS:
Generate 3 to 4 concise, factual sentences explaining the candidate's qualification for this role.
- Sentence 1: Overall fit, assigned tier ({packet.assigned_tier}), and experience level.
- Sentence 2: Key matched technical skills with supporting chunk citations e.g. [c_01].
- Sentence 3: Specific missing mandatory skills or qualification deficits.
- Sentence 4: Education credentials and relevant domain background [c_02].

Every statement regarding a candidate's background must cite the supporting chunk ID [c_XX].
Return a JSON object matching this schema:
{{
  "sentences": ["sentence 1...", "sentence 2 with [c_01]...", "sentence 3...", "sentence 4 with [c_02]..."],
  "citations": [["c_01"], ["c_01"], [], ["c_02"]],
  "summary_text": "sentence 1... sentence 2 [c_01]... sentence 3... sentence 4 [c_02]..."
}}
"""

    try:
        resp = await provider.complete(
            prompt=prompt,
            system_prompt=SYSTEM_GUARDRAIL_PROMPT,
            json_mode=True,
            max_tokens=1500,
            temperature=0.1,
        )
        explanation = await parse_and_repair_json(
            resp.content,
            CandidateExplanation,
            provider=provider,
            system_prompt=SYSTEM_GUARDRAIL_PROMPT,
            original_prompt=prompt,
        )
        return explanation, False, resp.prompt_tokens, resp.completion_tokens
    except Exception as e:
        logger.warning(f"Explainer agent failed: {e}. Falling back to deterministic template.")
        return generate_deterministic_explanation(packet), True, 0, 0
