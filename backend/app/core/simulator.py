"""
What-If Simulator for Recruiter Planning

Simulates candidate score and tier trajectories under hypothetical qualification additions
(e.g., candidate completes AWS certification, gains 2 years experience).

Core Principle: All outputs carry explicit disclaimer and are labelled as estimates.
"""

import copy
from typing import Any

from pydantic import BaseModel, Field

from app.core.features import extract_candidate_features
from app.core.jd_requirements import JobRequirements
from app.core.models import ResumeParseResult, WorkExperienceEntry
from app.core.scoring import CandidateScoreResult, WeightedBaselineScorer
from app.core.taxonomy import SkillTaxonomy
from app.core.tiers import TierAssignmentResult, assign_candidate_tier


class WhatIfSimulationResult(BaseModel):
    """Result of a hypothetical what-if candidate qualification simulation."""

    resume_id: str
    job_id: str | None = None
    base_score: float
    simulated_score: float
    score_delta: float
    base_tier: str
    simulated_tier: str
    tier_changed: bool
    hypothetical_skills_added: list[str] = Field(default_factory=list)
    hypothetical_years_added: float = 0.0
    newly_covered_must_skills: list[str] = Field(default_factory=list)
    newly_covered_nice_skills: list[str] = Field(default_factory=list)
    is_estimate: bool = True
    disclaimer: str = (
        "Hypothetical projection estimate for recruiter planning only. "
        "Not a verified qualification or guarantee of employment."
    )


def simulate_candidate_adjustments(
    parsed_resume: ResumeParseResult,
    job_reqs: JobRequirements,
    added_skills: list[str] | None = None,
    added_years: float = 0.0,
    scorer: Any | None = None,
    taxonomy: SkillTaxonomy | None = None,
) -> WhatIfSimulationResult:
    """
    Re-scores candidate under hypothetical qualification adjustments.
    Returns delta and new tier trajectory.
    """
    if scorer is None:
        scorer = WeightedBaselineScorer()
    if taxonomy is None:
        taxonomy = SkillTaxonomy.get_instance()

    hypo_skills = added_skills or []

    # 1. Base evaluation
    base_feats = extract_candidate_features(parsed_resume, job_reqs, taxonomy=taxonomy)
    base_score_res: CandidateScoreResult = scorer.score(base_feats)
    base_tier_res: TierAssignmentResult = assign_candidate_tier(
        base_score_res, base_feats, parse_confidence=parsed_resume.parse_confidence
    )

    # 2. Construct simulated candidate representation
    sim_resume = copy.deepcopy(parsed_resume)

    # Append hypothetical skills to raw text, scoring text, sections, and skills list
    if hypo_skills:
        hypo_str = ", ".join(hypo_skills)
        if "skills" in sim_resume.sections:
            sim_resume.sections["skills"] += f", {hypo_str}"
        else:
            sim_resume.sections["skills"] = hypo_str

        for skill in hypo_skills:
            sim_resume.scoring_text += f"\nHypothetical Skill: {skill}"
            sim_resume.raw_text += f"\nHypothetical Skill: {skill}"
            sim_resume.skills.append(skill)

    # Adjust experience if years added
    if added_years > 0.0:
        added_months = int(round(added_years * 12))
        sim_resume.scoring_text += f"\nExperience: {added_years:.1f} additional years"
        sim_resume.experiences.append(
            WorkExperienceEntry(
                title=job_reqs.title or "Professional Role",
                company="Simulated Experience",
                duration_months=added_months,
                raw_text=f"Simulated {added_years:.1f} years professional experience.",
            )
        )

    # 3. Simulated evaluation
    sim_feats = extract_candidate_features(sim_resume, job_reqs, taxonomy=taxonomy)
    sim_score_res: CandidateScoreResult = scorer.score(sim_feats)
    sim_tier_res: TierAssignmentResult = assign_candidate_tier(
        sim_score_res, sim_feats, parse_confidence=sim_resume.parse_confidence
    )

    # Detect newly covered skills
    base_must_covered = set(base_feats.matched_must_skills)
    sim_must_covered = set(sim_feats.matched_must_skills)
    new_must = sorted(sim_must_covered - base_must_covered)

    base_nice_covered = set(base_feats.matched_nice_skills)
    sim_nice_covered = set(sim_feats.matched_nice_skills)
    new_nice = sorted(sim_nice_covered - base_nice_covered)

    score_delta = round(sim_score_res.final_score - base_score_res.final_score, 4)

    return WhatIfSimulationResult(
        resume_id=parsed_resume.resume_id,
        job_id=job_reqs.job_id,
        base_score=base_score_res.final_score,
        simulated_score=sim_score_res.final_score,
        score_delta=score_delta,
        base_tier=base_tier_res.tier,
        simulated_tier=sim_tier_res.tier,
        tier_changed=(base_tier_res.tier != sim_tier_res.tier),
        hypothetical_skills_added=hypo_skills,
        hypothetical_years_added=added_years,
        newly_covered_must_skills=new_must,
        newly_covered_nice_skills=new_nice,
        is_estimate=True,
    )
