"""
Explainable Reasons Generator

Transforms mathematical feature attributions (additive weights or SHAP values) into
grounded, plain-language statements for recruiters (e.g., "Covers 5 of 6 must-have skills").

Core Principle: RAG Grounding is non-negotiable. Reasons clearly identify factual strengths
and gaps with cited evidence.
"""

from typing import Literal

from pydantic import BaseModel, Field

from app.core.features import CandidateFeatureVector
from app.core.jd_requirements import JobRequirements
from app.core.scoring import CandidateScoreResult


class ScoringReason(BaseModel):
    """A plain-language explanation of a specific feature's impact on candidate scoring."""

    category: Literal["strength", "gap", "neutral"]
    feature_name: str
    headline: str
    detail: str
    impact_score: float  # Numerical contribution to final score
    percentage_impact: float = 0.0


class CandidateReasonsSummary(BaseModel):
    """Consolidated explainable evaluation summary with plain-language reasons."""

    resume_id: str
    job_id: str | None = None
    final_score: float
    model_name: str
    summary_statement: str
    top_strengths: list[ScoringReason] = Field(default_factory=list)
    key_gaps: list[ScoringReason] = Field(default_factory=list)
    all_reasons: list[ScoringReason] = Field(default_factory=list)


def generate_candidate_reasons(
    score_result: CandidateScoreResult,
    feature_vector: CandidateFeatureVector,
    job_requirements: JobRequirements | None = None,
) -> CandidateReasonsSummary:
    """
    Generate plain-language explanations from model feature contributions.
    Maps quantitative features to unambiguous factual statements.
    """
    reasons: list[ScoringReason] = []

    # Map contribution objects by feature name
    contrib_map = {c.feature_name: c for c in score_result.feature_contributions}

    # 1. Must-Have Skills Reason
    must_cov = feature_vector.must_have_coverage.value
    matched_must = feature_vector.matched_must_skills
    missing_must = feature_vector.missing_must_skills
    total_must = len(matched_must) + len(missing_must)
    must_contrib = contrib_map.get("must_have_coverage")
    must_impact = must_contrib.contribution if must_contrib else 0.0
    must_pct = must_contrib.percentage_of_score if must_contrib else 0.0

    if total_must > 0:
        if must_cov >= 0.8:
            reasons.append(
                ScoringReason(
                    category="strength",
                    feature_name="must_have_coverage",
                    headline=(
                        f"Covers {len(matched_must)} of {total_must} "
                        f"must-have skills ({must_cov:.0%})"
                    ),
                    detail=(
                        f"Strong alignment on mandatory skills: {', '.join(matched_must[:5])}."
                        if matched_must
                        else "All required core skills matched."
                    ),
                    impact_score=must_impact,
                    percentage_impact=must_pct,
                )
            )
        elif must_cov >= 0.5:
            reasons.append(
                ScoringReason(
                    category="neutral",
                    feature_name="must_have_coverage",
                    headline=(
                        f"Partially covers {len(matched_must)} of {total_must} "
                        f"must-have skills ({must_cov:.0%})"
                    ),
                    detail=(
                        f"Matched: {', '.join(matched_must)}. "
                        f"Missing mandatory: {', '.join(missing_must)}."
                    ),
                    impact_score=must_impact,
                    percentage_impact=must_pct,
                )
            )
        else:
            reasons.append(
                ScoringReason(
                    category="gap",
                    feature_name="must_have_coverage",
                    headline=(
                        f"Missing {len(missing_must)} of {total_must} "
                        f"required skills ({must_cov:.0%} coverage)"
                    ),
                    detail=f"Critical missing skills: {', '.join(missing_must[:5])}.",
                    impact_score=must_impact,
                    percentage_impact=must_pct,
                )
            )

    # 2. Nice-to-Have Skills Reason
    matched_nice = feature_vector.matched_nice_skills
    nice_contrib = contrib_map.get("nice_to_have_coverage")
    nice_impact = nice_contrib.contribution if nice_contrib else 0.0
    nice_pct = nice_contrib.percentage_of_score if nice_contrib else 0.0

    if matched_nice:
        reasons.append(
            ScoringReason(
                category="strength",
                feature_name="nice_to_have_coverage",
                headline=f"Bonus: covers {len(matched_nice)} preferred skills",
                detail=f"Demonstrated secondary skills: {', '.join(matched_nice[:4])}.",
                impact_score=nice_impact,
                percentage_impact=nice_pct,
            )
        )

    # 3. Experience Years Gap Reason
    years_gap_val = feature_vector.years_gap.value
    years_is_missing = feature_vector.years_gap.is_missing
    years_contrib = contrib_map.get("years_gap_norm") or contrib_map.get("years_gap")
    years_impact = years_contrib.contribution if years_contrib else 0.0
    years_pct = years_contrib.percentage_of_score if years_contrib else 0.0

    min_yrs = job_requirements.min_years_experience if job_requirements else 0.0

    if not years_is_missing:
        if years_gap_val >= 1.0:
            reasons.append(
                ScoringReason(
                    category="strength",
                    feature_name="years_gap",
                    headline=f"Exceeds required experience by {years_gap_val:.1f} years",
                    detail=f"Candidate experience exceeds the {min_yrs:.1f}-year requirement.",
                    impact_score=years_impact,
                    percentage_impact=years_pct,
                )
            )
        elif years_gap_val >= -0.5:
            reasons.append(
                ScoringReason(
                    category="strength",
                    feature_name="years_gap",
                    headline=f"Meets experience requirement (~{min_yrs:.1f} years)",
                    detail="Candidate has adequate documented industry tenure.",
                    impact_score=years_impact,
                    percentage_impact=years_pct,
                )
            )
        else:
            deficit = abs(years_gap_val)
            reasons.append(
                ScoringReason(
                    category="gap",
                    feature_name="years_gap",
                    headline=f"Experience deficit: {deficit:.1f} years below requirement",
                    detail=(
                        f"Position requires {min_yrs:.1f} years; "
                        f"candidate tenure indicates a {deficit:.1f}-year gap."
                    ),
                    impact_score=years_impact,
                    percentage_impact=years_pct,
                )
            )
    else:
        reasons.append(
            ScoringReason(
                category="neutral",
                feature_name="years_gap",
                headline="Experience dates unverified",
                detail="Resume dates could not be parsed unambiguously; score was reweighted.",
                impact_score=0.0,
                percentage_impact=0.0,
            )
        )

    # 4. Education Match Reason
    edu_match = feature_vector.education_match.value
    edu_contrib = contrib_map.get("education_match")
    edu_impact = edu_contrib.contribution if edu_contrib else 0.0
    edu_pct = edu_contrib.percentage_of_score if edu_contrib else 0.0

    if edu_match >= 1.0:
        reasons.append(
            ScoringReason(
                category="strength",
                feature_name="education_match",
                headline="Education requirement fully satisfied",
                detail="Candidate holds degrees equal to or exceeding target criteria.",
                impact_score=edu_impact,
                percentage_impact=edu_pct,
            )
        )
    elif edu_match >= 0.5:
        reasons.append(
            ScoringReason(
                category="neutral",
                feature_name="education_match",
                headline="Partial education match",
                detail="Candidate degree is within 1 tier of required credential.",
                impact_score=edu_impact,
                percentage_impact=edu_pct,
            )
        )
    else:
        reasons.append(
            ScoringReason(
                category="gap",
                feature_name="education_match",
                headline="Education credential below job requirement",
                detail="Candidate does not meet the specified minimum academic rank.",
                impact_score=edu_impact,
                percentage_impact=edu_pct,
            )
        )

    # 5. Title Match Reason
    title_sim = feature_vector.title_match.value
    title_contrib = contrib_map.get("title_match")
    title_impact = title_contrib.contribution if title_contrib else 0.0
    title_pct = title_contrib.percentage_of_score if title_contrib else 0.0

    if title_sim >= 0.5:
        reasons.append(
            ScoringReason(
                category="strength",
                feature_name="title_match",
                headline="Direct past job title alignment",
                detail=(
                    f"Candidate past roles closely match target title "
                    f"(similarity {title_sim:.0%})."
                ),
                impact_score=title_impact,
                percentage_impact=title_pct,
            )
        )

    # 6. Skill Recency Reason
    recency = feature_vector.skill_recency.value
    recency_contrib = contrib_map.get("skill_recency")
    recency_impact = recency_contrib.contribution if recency_contrib else 0.0
    recency_pct = recency_contrib.percentage_of_score if recency_contrib else 0.0

    if recency >= 0.7:
        reasons.append(
            ScoringReason(
                category="strength",
                feature_name="skill_recency",
                headline=f"Active technical recency ({recency:.0%})",
                detail="Candidate actively utilized required tools in their most recent role.",
                impact_score=recency_impact,
                percentage_impact=recency_pct,
            )
        )

    # Segregate strengths and gaps
    strengths = [r for r in reasons if r.category == "strength"]
    gaps = [r for r in reasons if r.category == "gap"]

    # Generate overarching summary statement
    score_pct = score_result.final_score * 100.0
    if score_result.final_score >= 0.75:
        summary = (
            f"Strong match ({score_pct:.1f}%). Candidate covers {must_cov:.0%} of must-have skills "
            f"with demonstrated experience alignment."
        )
    elif score_result.final_score >= 0.50:
        summary = (
            f"Moderate match ({score_pct:.1f}%). Candidate covers {must_cov:.0%} of "
            f"must-have skills with some qualification or experience gaps."
        )
    else:
        summary = (
            f"Weak match ({score_pct:.1f}%). Candidate is missing key must-have skills "
            f"or exhibits significant role misalignment."
        )

    return CandidateReasonsSummary(
        resume_id=score_result.resume_id,
        job_id=score_result.job_id,
        final_score=score_result.final_score,
        model_name=score_result.model_name,
        summary_statement=summary,
        top_strengths=strengths,
        key_gaps=gaps,
        all_reasons=reasons,
    )
