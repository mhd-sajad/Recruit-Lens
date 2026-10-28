"""Unit tests for Explainable Reasons Generator."""

from app.core.features import CandidateFeatureVector, FeatureValue
from app.core.jd_requirements import JobRequirements
from app.core.reasons import CandidateReasonsSummary, generate_candidate_reasons
from app.core.scoring import CandidateScoreResult, FeatureContribution


def create_mock_score_and_features(
    must_cov: float = 1.0,
    years_gap: float = 2.0,
    edu_match: float = 1.0,
    matched_must: list[str] | None = None,
    missing_must: list[str] | None = None,
) -> tuple[CandidateScoreResult, CandidateFeatureVector]:
    def make_fv(name: str, val: float, mi: float, ma: float) -> FeatureValue:
        return FeatureValue(
            name=name,
            value=val,
            confidence=1.0,
            is_missing=False,
            min_bound=mi,
            max_bound=ma,
        )

    m_must = matched_must if matched_must is not None else ["Python", "Docker"]
    miss_must = missing_must if missing_must is not None else []

    fv = CandidateFeatureVector(
        resume_id="cand_reason_01",
        job_id="job_reason_01",
        must_have_coverage=make_fv("must_have_coverage", must_cov, 0.0, 1.0),
        nice_to_have_coverage=make_fv("nice_to_have_coverage", 0.5, 0.0, 1.0),
        matched_must_count=make_fv("matched_must_count", float(len(m_must)), 0.0, 50.0),
        matched_nice_count=make_fv("matched_nice_count", 1.0, 0.0, 50.0),
        inferred_count=make_fv("inferred_count", 0.0, 0.0, 50.0),
        missing_must_count=make_fv("missing_must_count", float(len(miss_must)), 0.0, 50.0),
        years_gap=make_fv("years_gap", years_gap, -10.0, 15.0),
        seniority_gap=make_fv("seniority_gap", 0.0, -4.0, 4.0),
        education_match=make_fv("education_match", edu_match, 0.0, 1.0),
        title_match=make_fv("title_match", 0.8, 0.0, 1.0),
        skill_recency=make_fv("skill_recency", 0.85, 0.0, 1.0),
        dense_similarity=make_fv("dense_similarity", 0.8, 0.0, 1.0),
        matched_must_skills=m_must,
        missing_must_skills=miss_must,
        matched_nice_skills=["Kubernetes"],
    )

    contribs = [
        FeatureContribution(
            feature_name="must_have_coverage",
            feature_value=must_cov,
            contribution=0.35 * must_cov,
            percentage_of_score=40.0,
        ),
        FeatureContribution(
            feature_name="years_gap_norm",
            feature_value=0.7,
            contribution=0.08,
            percentage_of_score=10.0,
        ),
    ]

    score_res = CandidateScoreResult(
        resume_id="cand_reason_01",
        job_id="job_reason_01",
        final_score=0.82,
        model_name="weighted_baseline",
        feature_contributions=contribs,
        base_value=0.0,
        overall_confidence=0.95,
    )

    return score_res, fv


def test_generate_candidate_reasons_strong_match() -> None:
    job = JobRequirements(
        title="Senior Python Engineer",
        min_years_experience=3.0,
        must_have_skills=["Python", "Docker"],
    )
    score_res, fv = create_mock_score_and_features(must_cov=1.0, years_gap=2.5)

    reasons_summary = generate_candidate_reasons(score_res, fv, job_requirements=job)
    assert isinstance(reasons_summary, CandidateReasonsSummary)
    assert "Strong match" in reasons_summary.summary_statement
    assert len(reasons_summary.top_strengths) >= 2
    assert len(reasons_summary.key_gaps) == 0

    must_reason = next(
        r for r in reasons_summary.top_strengths if r.feature_name == "must_have_coverage"
    )
    assert "Covers 2 of 2 must-have skills (100%)" in must_reason.headline


def test_generate_candidate_reasons_with_gaps() -> None:
    job = JobRequirements(
        title="Senior Python Engineer",
        min_years_experience=5.0,
        must_have_skills=["Python", "Docker", "Go", "Rust"],
    )
    score_res, fv = create_mock_score_and_features(
        must_cov=0.25,
        years_gap=-3.0,
        matched_must=["Python"],
        missing_must=["Docker", "Go", "Rust"],
    )
    score_res.final_score = 0.35

    reasons_summary = generate_candidate_reasons(score_res, fv, job_requirements=job)
    assert "Weak match" in reasons_summary.summary_statement
    assert len(reasons_summary.key_gaps) >= 1

    gap_features = [r.feature_name for r in reasons_summary.key_gaps]
    assert "must_have_coverage" in gap_features
    assert "years_gap" in gap_features
