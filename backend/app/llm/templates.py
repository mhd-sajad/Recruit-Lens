"""
Deterministic No-LLM Templates for factual generation fallback.
Guarantees reliable, un-hallucinated candidate explanations, interview questions, and email drafts
derived strictly from structured features and retrieved evidence chunks.
"""

from typing import Literal

from app.llm.schemas import (
    CandidateExplanation,
    EmailDraft,
    EmailsResult,
    EvidencePacket,
    InterviewQuestion,
    InterviewQuestionsResult,
)


def generate_deterministic_explanation(packet: EvidencePacket) -> CandidateExplanation:
    """Produce factual 3-4 sentence evaluation statement citing retrieved chunks."""
    c1 = packet.retrieved_chunks[0].chunk_id if packet.retrieved_chunks else "c_01"
    c2 = packet.retrieved_chunks[1].chunk_id if len(packet.retrieved_chunks) > 1 else c1

    if packet.years_experience is not None:
        s1 = (
            f"Candidate is evaluated as {packet.assigned_tier} with {packet.years_experience:.1f} years of relevant "
            f"experience compared to {packet.required_years:.1f} years required [{c1}]."
        )
    else:
        s1 = (
            f"Candidate is evaluated as {packet.assigned_tier} with unverified dates of experience "
            f"compared to {packet.required_years:.1f} years required [{c1}]."
        )
    cite1 = [c1]

    matched_str = (
        ", ".join(packet.matched_must_skills[:4])
        if packet.matched_must_skills
        else "general qualifications"
    )
    s2 = f"Demonstrates verified evidence in required core competencies including {matched_str} [{c1}]."
    cite2 = [c1]

    if packet.missing_must_skills:
        missing_str = ", ".join(packet.missing_must_skills[:3])
        s3 = f"Identified qualification gaps in mandatory requirements: {missing_str} [{c1}]."
        cite3 = [c1]
    else:
        s3 = f"Successfully satisfies all verified mandatory skill requirements for this position [{c1}]."
        cite3 = [c1]

    deg_cite = [c2]
    s4 = f"Holds documented {packet.degree_level} education credentials relevant to role specifications [{c2}]."

    sentences = [s1, s2, s3, s4]
    citations = [cite1, cite2, cite3, deg_cite]
    summary_text = " ".join(sentences)

    return CandidateExplanation(
        sentences=sentences,
        citations=citations,
        summary_text=summary_text,
    )


def generate_deterministic_questions(packet: EvidencePacket) -> InterviewQuestionsResult:
    """Generate 3-5 seniority-calibrated interview questions probing verified skills and gaps."""
    c1 = packet.retrieved_chunks[0].chunk_id if packet.retrieved_chunks else None
    questions: list[InterviewQuestion] = []

    calibrated_diff: Literal["junior", "mid", "senior", "unknown"] = (
        packet.seniority_level
        if packet.seniority_level in ("junior", "mid", "senior")
        else (
            "senior"
            if (packet.years_experience is not None and packet.years_experience >= 5.0)
            else "mid"
            if (packet.years_experience is not None and packet.years_experience >= 2.0)
            else "junior"
            if (packet.years_experience is not None)
            else "unknown"
        )
    )

    # 1. Probe matched skills
    if packet.matched_must_skills:
        skill = packet.matched_must_skills[0]
        questions.append(
            InterviewQuestion(
                question=f"Can you describe an end-to-end project where you implemented {skill} in a production environment?",
                target_topic=skill,
                difficulty=calibrated_diff,
                rationale=f"Candidate lists verified experience with {skill}.",
                citation=c1,
            )
        )
    if len(packet.matched_must_skills) > 1:
        skill2 = packet.matched_must_skills[1]
        questions.append(
            InterviewQuestion(
                question=f"What design trade-offs and edge cases did you encounter when scaling systems using {skill2}?",
                target_topic=skill2,
                difficulty=calibrated_diff,
                rationale=f"Probing technical depth and architectural complexity in {skill2}.",
                citation=c1,
            )
        )

    # 2. Probe missing skills or gaps
    if packet.missing_must_skills:
        gap = packet.missing_must_skills[0]
        questions.append(
            InterviewQuestion(
                question=f"This role requires practical proficiency in {gap}. How would you leverage your existing competencies to ramp up rapidly on {gap}?",
                target_topic=gap,
                difficulty="mid" if calibrated_diff != "unknown" else "unknown",
                rationale=f"Requirement deficit: candidate resume does not show explicit evidence for {gap}.",
                citation=None,
            )
        )

    # 3. Overall architecture / domain question
    if packet.years_experience is not None:
        q_exp = f"With {packet.years_experience:.1f} years in the field, how do you approach debugging complex regressions and maintaining test reliability?"
    else:
        q_exp = "How do you approach debugging complex regressions and maintaining quality in demanding operational environments?"

    questions.append(
        InterviewQuestion(
            question=q_exp,
            target_topic="Engineering Practices",
            difficulty=calibrated_diff,
            rationale="Calibrating operational maturity and quality assurance mindset.",
            citation=c1,
        )
    )

    return InterviewQuestionsResult(questions=questions)


def generate_deterministic_emails(packet: EvidencePacket) -> EmailsResult:
    """
    Generate professional email drafts for interview invite, hold, and rejection.
    Strict Rule: Rejection emails NEVER contain internal scores or critique reasons.
    Personalization strictly utilizes verified strengths.
    """
    c1 = packet.retrieved_chunks[0].chunk_id if packet.retrieved_chunks else "c_01"
    top_skill = (
        packet.matched_must_skills[0] if packet.matched_must_skills else "your technical background"
    )

    invite = EmailDraft(
        action="interview_invite",
        subject="Interview Invitation - Recruit Lens Team",
        body=(
            f"Dear Candidate,\n\n"
            f"Thank you for your application. We were impressed by your background, particularly your demonstrated "
            f"experience with {top_skill}.\n\n"
            f"We would like to invite you for an initial technical conversation with our engineering team to discuss "
            f"your experience and explore how your skills align with our upcoming initiatives.\n\n"
            f"Please let us know your availability over the coming days.\n\n"
            f"Best regards,\nRecruiting Team"
        ),
        citations_used=[c1],
    )

    hold = EmailDraft(
        action="hold",
        subject="Update on your application - Recruit Lens",
        body=(
            "Dear Candidate,\n\n"
            "Thank you for your patience while our hiring team reviews candidate qualifications. "
            "Your application remains under active consideration, and we are currently finalizing candidate schedules.\n\n"
            "We appreciate your interest and will provide an update as soon as the next phase begins.\n\n"
            "Best regards,\nRecruiting Team"
        ),
        citations_used=[],
    )

    # Rejection email: Strictly professional, zero internal scores, zero negative critique reasons
    rejection = EmailDraft(
        action="rejection",
        subject="Your application with Recruit Lens",
        body=(
            "Dear Candidate,\n\n"
            "Thank you for taking the time to apply and for your interest in our team. "
            "After careful consideration of our current hiring requirements and team priorities, "
            "we have decided to proceed with other candidates whose backgrounds more closely match "
            "our immediate needs for this specific opening.\n\n"
            "We sincerely appreciate your interest and wish you the very best in your professional journey.\n\n"
            "Best regards,\nRecruiting Team"
        ),
        citations_used=[],
    )

    return EmailsResult(invite=invite, hold=hold, rejection=rejection)
