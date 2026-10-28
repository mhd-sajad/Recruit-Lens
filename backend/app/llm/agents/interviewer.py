"""
Interview Question Generator Agent.
Produces 3 to 5 seniority-calibrated interview questions probing matched competencies and unverified gaps.
"""

from app.llm.guardrails import SYSTEM_GUARDRAIL_PROMPT, format_evidence_block
from app.llm.provider import BaseLLMProvider
from app.llm.repair import parse_and_repair_json
from app.llm.schemas import EvidencePacket, InterviewQuestionsResult
from app.llm.templates import generate_deterministic_questions
from app.logging import get_logger

logger = get_logger("agents.interviewer")


async def generate_candidate_questions(
    packet: EvidencePacket,
    provider: BaseLLMProvider,
) -> tuple[InterviewQuestionsResult, bool, int, int]:
    """
    Generate 3-5 tailored interview questions.
    Returns: (InterviewQuestionsResult, is_fallback, prompt_tokens, completion_tokens)
    """
    if provider.provider_name == "no_llm":
        return generate_deterministic_questions(packet), True, 0, 0

    evidence_str = "\n\n".join(
        format_evidence_block(c.chunk_id, c.section, c.text) for c in packet.retrieved_chunks
    )

    matched_str = ", ".join(packet.matched_must_skills) if packet.matched_must_skills else "None"
    missing_str = ", ".join(packet.missing_must_skills) if packet.missing_must_skills else "None"

    calibrated_level = (
        "senior"
        if packet.years_experience >= 5.0
        else ("mid" if packet.years_experience >= 2.0 else "junior")
    )

    prompt = f"""INTERVIEW QUESTION GENERATION TASK:
Candidate ID: {packet.candidate_id}
Experience: {packet.years_experience:.1f} years (Calibrated baseline: {calibrated_level})
Matched Skills to verify: {matched_str}
Skill gaps to probe: {missing_str}

CANDIDATE EVIDENCE CHUNKS:
{evidence_str}

INSTRUCTIONS:
Generate 3 to 5 tailored interview questions calibrated to the candidate's seniority:
1. Verification Questions: Formulate in-depth questions probing candidate claims in matched skills. Must cite supporting chunk ID [c_XX].
2. Gap Probing Questions: Formulate scenario-based questions exploring missing or unverified skill areas ({missing_str}).
3. Calibration: Set difficulty strictly to "junior", "mid", or "senior" based on question complexity.

Return a JSON object matching this schema:
{{
  "questions": [
    {{
      "question": "Question text...",
      "target_topic": "Topic name (e.g. Python, Microservices, Testing)",
      "difficulty": "junior" | "mid" | "senior",
      "rationale": "Why this question tests candidate fit...",
      "citation": "c_01" or null
    }}
  ]
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
        questions = await parse_and_repair_json(
            resp.content,
            InterviewQuestionsResult,
            provider=provider,
            system_prompt=SYSTEM_GUARDRAIL_PROMPT,
            original_prompt=prompt,
        )
        return questions, False, resp.prompt_tokens, resp.completion_tokens
    except Exception as e:
        logger.warning(f"Interviewer agent failed: {e}. Falling back to deterministic template.")
        return generate_deterministic_questions(packet), True, 0, 0
