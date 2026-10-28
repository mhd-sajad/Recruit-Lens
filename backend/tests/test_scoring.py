"""Unit tests for Candidate Scoring Engine (Weighted Baseline & Monotonic XGBoost)."""

from app.core.features import CandidateFeatureVector, FeatureValue
from app.core.scoring import (
    CandidateScoreResult,
    MonotonicXGBoostScorer,
    WeightedBaselineScorer,
)


def create_feature_vector(
    must_cov: float = 1.0,
    nice_cov: float = 0.5,
    missing_must: float = 0.0,
    years_gap: float = 2.0,
    is_missing_years: bool = False,
) -> CandidateFeatureVector:
    def make_fv(
        name: str,
        val: float,
        mi: float,
        ma: float,
        is_miss: bool = False,
    ) -> FeatureValue:
        return FeatureValue(
            name=name,
            value=val,
            confidence=0.0 if is_miss else 1.0,
            is_missing=is_miss,
            missing_reason="Not provided" if is_miss else None,
            min_bound=mi,
            max_bound=ma,
        )

    return CandidateFeatureVector(
        resume_id="cand_test_01",
        job_id="job_test_01",
        must_have_coverage=make_fv("must_have_coverage", must_cov, 0.0, 1.0),
        nice_to_have_coverage=make_fv("nice_to_have_coverage", nice_cov, 0.0, 1.0),
        matched_must_count=make_fv("matched_must_count", 3.0 * must_cov, 0.0, 50.0),
        matched_nice_count=make_fv("matched_nice_count", 2.0 * nice_cov, 0.0, 50.0),
        inferred_count=make_fv("inferred_count", 0.0, 0.0, 50.0),
        missing_must_count=make_fv("missing_must_count", missing_must, 0.0, 50.0),
        years_gap=make_fv("years_gap", years_gap, -10.0, 15.0, is_miss=is_missing_years),
        seniority_gap=make_fv("seniority_gap", 0.0, -4.0, 4.0),
        education_match=make_fv("education_match", 1.0, 0.0, 1.0),
        title_match=make_fv("title_match", 0.8, 0.0, 1.0),
        skill_recency=make_fv("skill_recency", 0.9, 0.0, 1.0),
        dense_similarity=make_fv("dense_similarity", 0.75, 0.0, 1.0),
    )


def test_weighted_baseline_scorer_exact_attribution() -> None:
    scorer = WeightedBaselineScorer()
    fv = create_feature_vector(must_cov=1.0, nice_cov=0.5)
    res = scorer.score(fv)

    assert isinstance(res, CandidateScoreResult)
    assert res.model_name == "weighted_baseline"
    assert 0.0 <= res.final_score <= 1.0
    assert len(res.feature_contributions) > 0

    # Verify sum of contributions equals final score within rounding tolerance
    contrib_sum = sum(c.contribution for c in res.feature_contributions)
    assert abs(contrib_sum - res.final_score) < 0.005


def test_weighted_baseline_missing_data_reweighting() -> None:
    scorer = WeightedBaselineScorer()
    fv_missing = create_feature_vector(is_missing_years=True)
    res = scorer.score(fv_missing)

    assert any(
        c.is_missing and c.feature_name == "years_gap_norm" for c in res.feature_contributions
    )
    assert len(res.data_missing_warnings) > 0
    # Missing feature should have 0 contribution, but total score shouldn't be zeroed
    assert res.final_score > 0.5


def test_monotonic_xgboost_scorer_monotonicity() -> None:
    import numpy as np

    scorer = MonotonicXGBoostScorer()
    # Create simple monotonic training data
    x_tr = np.zeros((20, 12), dtype=np.float32)
    y_tr = np.zeros(20, dtype=np.float32)

    for i in range(20):
        cov = i / 20.0
        x_tr[i, 0] = cov  # must_have_coverage
        x_tr[i, 2] = cov * 4  # matched_must_count
        x_tr[i, 5] = (1.0 - cov) * 4  # missing_must_count
        y_tr[i] = 0.2 + 0.7 * cov

    scorer.train(x_tr, y_tr, params={"n_estimators": 20, "max_depth": 2})

    # Test monotonicity: increasing must_have_coverage must never decrease score
    scores: list[float] = []
    for cov_val in [0.1, 0.3, 0.5, 0.7, 0.9, 1.0]:
        fv = create_feature_vector(must_cov=cov_val, missing_must=(1.0 - cov_val) * 4)
        score = scorer.score(fv).final_score
        scores.append(score)

    for i in range(len(scores) - 1):
        assert scores[i] <= scores[i + 1] + 1e-5, f"Monotonicity violation at step {i}: {scores}"
