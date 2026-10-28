"""
Email Drafter Agent.
Generates personalized candidate communication drafts:
- Interview Invitation: Highlight verified candidate strengths.
- Application On Hold: Reassuring update while schedules finalize.
- Polite Rejection: Strictly professional; NEVER contains internal scores or critique reasons.
"""

from app.llm.guardrails import SYSTEM_GUARDRAIL_PROMPT, format_evidence_block
from app.llm.provider import BaseLLMProvider
from app.llm.repair import parse_and_repair_json
from app.llm.schemas import EmailsResult, EvidencePacket
from app.llm.templates import generate_deterministic_emails
from app.logging import get_logger

logger = get_logger("agents.emailer")


async def generate_candidate_emails(
    packet: EvidencePacket,
    provider: BaseLLMProvider,
) -> tuple[EmailsResult, bool, int, int]:
    """
    Generate professional email drafts for invite, hold, and rejection actions.
    Returns: (EmailsResult, is_fallback, prompt_tokens, completion_tokens)
    """
    if provider.provider_name == "no_llm":
        return generate_deterministic_emails(packet), True, 0, 0

    evidence_str = "\n\n".join(
        format_evidence_block(c.chunk_id, c.section, c.text) for c in packet.retrieved_chunks
    )

    top_skills_str = (
        ", ".join(packet.matched_must_skills[:3])
        if packet.matched_must_skills
        else "technical experience"
    )

    prompt = f"""EMAIL DRAFTING TASK:
Candidate ID: {packet.candidate_id}
Assigned Tier: {packet.assigned_tier}
Verified Strengths to reference in invitation: {top_skills_str}

CANDIDATE EVIDENCE CHUNKS:
{evidence_str}

INSTRUCTIONS:
Generate 3 distinct email drafts:
1. "interview_invite": Friendly invitation referencing verified candidate strengths in {top_skills_str}.
2. "hold": Warm update notifying the candidate that review is ongoing.
3. "rejection": Courteous, respectful rejection.
   CRITICAL SAFETY RULE FOR REJECTION: NEVER include internal scores, numerical ratings, or negative critique reasons.
   Express appreciation for their time and wish them well in their search.

Return a JSON object matching this schema:
{{
  "invite": {{
    "action": "interview_invite",
    "subject": "Interview Invitation: ...",
    "body": "Dear Candidate, ...",
    "citations_used": ["c_01"]
  }},
  "hold": {{
    "action": "hold",
    "subject": "Application Update: ...",
    "body": "Dear Candidate, ...",
    "citations_used": []
  }},
  "rejection": {{
    "action": "rejection",
    "subject": "Your application with Recruit Lens",
    "body": "Dear Candidate, ...",
    "citations_used": []
  }}
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
        emails = await parse_and_repair_json(
            resp.content,
            EmailsResult,
            provider=provider,
            system_prompt=SYSTEM_GUARDRAIL_PROMPT,
            original_prompt=prompt,
        )
        # Enforce rejection email safety post-validation
        if any(
            word in emails.rejection.body.lower()
            for word in ["score", "rating", "critique", "failed", "deficit"]
        ):
            logger.warning(
                "Safety guard triggered: Rejection email contained forbidden score/deficit language. Reverting to safe template."
            )
            emails.rejection = generate_deterministic_emails(packet).rejection

        return emails, False, resp.prompt_tokens, resp.completion_tokens
    except Exception as e:
        logger.warning(f"Emailer agent failed: {e}. Falling back to deterministic template.")
        return generate_deterministic_emails(packet), True, 0, 0
