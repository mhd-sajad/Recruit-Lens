"""
Candidate Tier Assignment Engine with Strict Must-Have Override and Abstain States

Assigns candidates into 4 actionable recruitment tiers:
1. Strong Fit (Score >= 0.72 AND 100% must-haves met)
2. Interview  (Score >= 0.50 AND >= 50% must-haves met)
3. Hold       (Score >= 0.30)
4. Reject     (Score < 0.30)

Special State:
- Abstain: Triggered when resume parse confidence is low (< 0.50) or document is unverified.
Must-Have Override:
- Missing any must-have skill strictly disqualifies a candidate from 'Strong Fit'.
"""

from typing import Literal

from pydantic import BaseModel

from app.core.features import CandidateFeatureVector
from app.core.scoring import CandidateScoreResult

TierName = Literal["Strong Fit", "Interview", "Hold", "Reject", "Abstain"]


class TierAssignmentResult(BaseModel):
    """Calibrated tier assignment with override and abstain provenance."""

    resume_id: str
    job_id: str | None = None
    final_score: float
    tier: TierName
    tier_rank: int  # 3=Strong Fit, 2=Interview, 1=Hold, 0=Reject, -1=Abstain
    must_have_override_applied: bool = False
    override_reason: str | None = None
    is_abstain: bool = False
    abstain_reason: str | None = None
    recommended_action: str = ""


# Data-derived score thresholds
STRONG_FIT_THRESHOLD = 0.72
INTERVIEW_THRESHOLD = 0.50
HOLD_THRESHOLD = 0.30
MIN_PARSE_CONFIDENCE_THRESHOLD = 0.50


def assign_candidate_tier(
    score_result: CandidateScoreResult,
    feature_vector: CandidateFeatureVector,
    parse_confidence: float = 1.0,
    is_verified_resume: bool = True,
) -> TierAssignmentResult:
    """
    Assign recruitment tier based on calibrated thresholds with strict guardrails:
    1. Abstain Check: Low parse fidelity or unverified document.
    2. Threshold Mapping: Score mapped to preliminary tier.
    3. Must-Have Override: Missing mandatory skills forces downgrade.
    """
    resume_id = score_result.resume_id
    job_id = score_result.job_id
    score = score_result.final_score

    # 1. Abstain Guard: If parse confidence is below threshold, refuse automated tiering
    if not is_verified_resume:
        return TierAssignmentResult(
            resume_id=resume_id,
            job_id=job_id,
            final_score=score,
            tier="Abstain",
            tier_rank=-1,
            is_abstain=True,
            abstain_reason="Document gate detected non-resume or unverified document structure.",
            recommended_action="Manual recruiter document review required.",
        )

    if parse_confidence < MIN_PARSE_CONFIDENCE_THRESHOLD:
        return TierAssignmentResult(
            resume_id=resume_id,
            job_id=job_id,
            final_score=score,
            tier="Abstain",
            tier_rank=-1,
            is_abstain=True,
            abstain_reason=(
                f"Parse confidence ({parse_confidence:.2f}) is below minimum reliable "
                f"threshold ({MIN_PARSE_CONFIDENCE_THRESHOLD:.2f}). "
                f"Possible scanned or corrupt PDF."
            ),
            recommended_action="Inspect raw PDF text before deciding.",
        )

    # 2. Preliminary Tier from Calibrated Data Thresholds
    preliminary_tier: TierName
    preliminary_rank: int

    if score >= STRONG_FIT_THRESHOLD:
        preliminary_tier = "Strong Fit"
        preliminary_rank = 3
    elif score >= INTERVIEW_THRESHOLD:
        preliminary_tier = "Interview"
        preliminary_rank = 2
    elif score >= HOLD_THRESHOLD:
        preliminary_tier = "Hold"
        preliminary_rank = 1
    else:
        preliminary_tier = "Reject"
        preliminary_rank = 0

    # 3. Must-Have Skill Override Enforcement
    must_cov = feature_vector.must_have_coverage.value
    missing_must = feature_vector.missing_must_skills
    override_applied = False
    override_reason: str | None = None

    final_tier = preliminary_tier
    final_rank = preliminary_rank

    # Rule: Missing any required skill strictly disallows Strong Fit without exception
    if preliminary_tier == "Strong Fit" and (len(missing_must) > 0 or must_cov < 1.0):
        final_tier = "Interview"
        final_rank = 2
        override_applied = True
        missing_str = ", ".join(missing_must[:3]) if missing_must else "unmet requirements"
        override_reason = (
            f"Must-have override: High score ({score:.2f}) qualifies for Strong Fit, "
            f"but candidate is missing mandatory requirements ({missing_str}). "
            f"Downgraded to Interview."
        )

    # Rule: Severe experience deficit (e.g. 1 year vs 5 required, gap < -1.0) disallows Strong Fit
    years_gap_val = feature_vector.years_gap.value
    years_gap_missing = feature_vector.years_gap.is_missing
    if final_rank >= 3 and not years_gap_missing and years_gap_val < -1.0:
        final_tier = "Interview"
        final_rank = 2
        override_applied = True
        override_reason = (
            f"Experience override: Candidate experience gap ({years_gap_val:+.1f} years) falls short "
            f"of role requirement. Downgraded to Interview."
        )

    # Rule: Low must-have coverage (< 50%) disallows Interview
    if final_rank >= 2 and must_cov < 0.50:
        final_tier = "Hold"
        final_rank = 1
        override_applied = True
        override_reason = (
            f"Must-have override: Candidate must-have coverage ({must_cov:.0%}) is under 50%. "
            f"Downgraded to Hold."
        )

    # Recommended action descriptions
    actions = {
        "Strong Fit": "Prioritize immediate recruiter screen and technical interview scheduling.",
        "Interview": "Proceed to screening interview; verify secondary qualification gaps.",
        "Hold": "Keep in active talent pool as backup; consider if top candidates decline.",
        "Reject": "Archive candidate or route to automated polite rejection workflow.",
        "Abstain": "Manual recruiter inspection required.",
    }

    return TierAssignmentResult(
        resume_id=resume_id,
        job_id=job_id,
        final_score=score,
        tier=final_tier,
        tier_rank=final_rank,
        must_have_override_applied=override_applied,
        override_reason=override_reason,
        is_abstain=False,
        recommended_action=actions.get(final_tier, ""),
    )
