"""Unit tests for Candidate Tier Assignment Engine."""

from app.core.features import CandidateFeatureVector, FeatureValue
from app.core.scoring import CandidateScoreResult
from app.core.tiers import assign_candidate_tier


def create_mock_score_and_vector(
    score: float,
    must_cov: float = 1.0,
    missing_must: list[str] | None = None,
) -> tuple[CandidateScoreResult, CandidateFeatureVector]:
    def make_fv(name: str, val: float, mi: float, ma: float) -> FeatureValue:
        return FeatureValue(
            name=name, value=val, confidence=1.0, is_missing=False, min_bound=mi, max_bound=ma
        )

    miss_m = missing_must or []
    m_must = ["Python", "Docker"] if must_cov > 0.5 else ["Python"]

    fv = CandidateFeatureVector(
        resume_id="cand_tier_01",
        job_id="job_tier_01",
        must_have_coverage=make_fv("must_have_coverage", must_cov, 0.0, 1.0),
        nice_to_have_coverage=make_fv("nice_to_have_coverage", 0.5, 0.0, 1.0),
        matched_must_count=make_fv("matched_must_count", float(len(m_must)), 0.0, 50.0),
        matched_nice_count=make_fv("matched_nice_count", 1.0, 0.0, 50.0),
        inferred_count=make_fv("inferred_count", 0.0, 0.0, 50.0),
        missing_must_count=make_fv("missing_must_count", float(len(miss_m)), 0.0, 50.0),
        years_gap=make_fv("years_gap", 2.0, -10.0, 15.0),
        seniority_gap=make_fv("seniority_gap", 0.0, -4.0, 4.0),
        education_match=make_fv("education_match", 1.0, 0.0, 1.0),
        title_match=make_fv("title_match", 0.8, 0.0, 1.0),
        skill_recency=make_fv("skill_recency", 0.85, 0.0, 1.0),
        dense_similarity=make_fv("dense_similarity", 0.8, 0.0, 1.0),
        matched_must_skills=m_must,
        missing_must_skills=miss_m,
    )

    score_res = CandidateScoreResult(
        resume_id="cand_tier_01",
        job_id="job_tier_01",
        final_score=score,
        model_name="weighted_baseline",
    )
    return score_res, fv


def test_assign_tier_strong_fit() -> None:
    score_res, fv = create_mock_score_and_vector(score=0.85, must_cov=1.0)
    tier_res = assign_candidate_tier(score_res, fv, parse_confidence=0.95)

    assert tier_res.tier == "Strong Fit"
    assert tier_res.tier_rank == 3
    assert not tier_res.must_have_override_applied
    assert not tier_res.is_abstain


def test_assign_tier_must_have_override() -> None:
    # High score (0.80) but missing a mandatory skill ("Docker")
    score_res, fv = create_mock_score_and_vector(score=0.80, must_cov=0.66, missing_must=["Docker"])
    tier_res = assign_candidate_tier(score_res, fv, parse_confidence=0.95)

    # Must be downgraded from Strong Fit to Interview
    assert tier_res.tier == "Interview"
    assert tier_res.tier_rank == 2
    assert tier_res.must_have_override_applied
    assert "Must-have override" in (tier_res.override_reason or "")


def test_assign_tier_abstain_on_low_parse_confidence() -> None:
    score_res, fv = create_mock_score_and_vector(score=0.85, must_cov=1.0)
    # Parse confidence 0.30 triggers abstain
    tier_res = assign_candidate_tier(score_res, fv, parse_confidence=0.30)

    assert tier_res.tier == "Abstain"
    assert tier_res.tier_rank == -1
    assert tier_res.is_abstain
    assert "below minimum reliable threshold" in (tier_res.abstain_reason or "")


def test_assign_tier_abstain_on_unverified_document() -> None:
    score_res, fv = create_mock_score_and_vector(score=0.85, must_cov=1.0)
    tier_res = assign_candidate_tier(score_res, fv, is_verified_resume=False)

    assert tier_res.tier == "Abstain"
    assert tier_res.is_abstain
    assert "non-resume" in (tier_res.abstain_reason or "")
