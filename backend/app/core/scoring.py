"""
Scoring Engine: Explainable Candidate Scoring Models

Provides two scoring implementations:
1. WeightedBaselineScorer: Deterministic, transparent linear combination with missing-data
   reweighting and exact additive feature attributions.
2. MonotonicXGBoostScorer: Gradient boosted trees with strict monotonic constraints
   (e.g., more matched must-haves or higher coverage never lowers candidate score).

Core Principle: Scoring NEVER uses an LLM. Zero hallucinations; strict deterministic grounding.
"""

import logging
from typing import Any, Literal

import numpy as np
from pydantic import BaseModel, Field

from app.core.features import CandidateFeatureVector

logger = logging.getLogger(__name__)

# Ordered feature keys for model inputs
FEATURE_ORDER: list[str] = [
    "must_have_coverage",
    "nice_to_have_coverage",
    "matched_must_count",
    "matched_nice_count",
    "inferred_count",
    "missing_must_count",
    "years_gap",
    "seniority_gap",
    "education_match",
    "title_match",
    "skill_recency",
    "dense_similarity",
]

# Monotonic constraints: +1 = positive, -1 = negative, 0 = unconstrained
# Missing must count must strictly decrease or hold score; all others increase or hold
MONOTONIC_CONSTRAINTS: tuple[int, ...] = (1, 1, 1, 1, 1, -1, 1, 0, 1, 1, 1, 1)

# Default baseline weights for normalized features
DEFAULT_BASELINE_WEIGHTS: dict[str, float] = {
    "must_have_coverage": 0.35,
    "nice_to_have_coverage": 0.12,
    "title_match": 0.15,
    "dense_similarity": 0.12,
    "education_match": 0.08,
    "years_gap_norm": 0.08,
    "skill_recency": 0.06,
    "seniority_gap_norm": 0.04,
}


class FeatureContribution(BaseModel):
    """Explainable additive contribution of a single feature to the final score."""

    feature_name: str
    feature_value: float
    contribution: float
    percentage_of_score: float
    is_missing: bool = False


class CandidateScoreResult(BaseModel):
    """Structured scoring output with complete explainability provenance."""

    resume_id: str
    job_id: str | None = None
    final_score: float = Field(ge=0.0, le=1.0)
    model_name: Literal["weighted_baseline", "monotonic_xgboost"]
    feature_contributions: list[FeatureContribution] = Field(default_factory=list)
    base_value: float = 0.0
    overall_confidence: float = Field(ge=0.0, le=1.0, default=1.0)
    data_missing_warnings: list[str] = Field(default_factory=list)


def normalize_years_gap(gap: float) -> float:
    """Normalize years gap from [-5.0, +5.0] to [0.0, 1.0]."""
    # -5 years or worse -> 0.0; +5 years or more -> 1.0; 0 years -> 0.5
    return float(np.clip((gap + 5.0) / 10.0, 0.0, 1.0))


def normalize_seniority_gap(gap: float) -> float:
    """Normalize seniority gap from [-2.0, +2.0] to [0.0, 1.0]."""
    return float(np.clip((gap + 2.0) / 4.0, 0.0, 1.0))


class WeightedBaselineScorer:
    """
    Transparent, explainable linear scorer.
    Dynamically reweights present features when data is missing rather than
    silently penalizing candidates with 0.
    """

    def __init__(self, weights: dict[str, float] | None = None) -> None:
        if weights and any(k in DEFAULT_BASELINE_WEIGHTS for k in weights):
            self.weights = {
                k: float(v) for k, v in weights.items() if k in DEFAULT_BASELINE_WEIGHTS
            }
        elif weights and any(
            k in ("skills", "experience", "education", "semantic") for k in weights
        ):
            w_sk = float(weights.get("skills", 0.4))
            w_exp = float(weights.get("experience", 0.3))
            w_edu = float(weights.get("education", 0.15))
            w_sem = float(weights.get("semantic", 0.15))
            self.weights = {
                "must_have_coverage": w_sk * 0.8,
                "nice_to_have_coverage": w_sk * 0.2,
                "years_gap_norm": w_exp * 0.6,
                "title_match": w_exp * 0.25,
                "seniority_gap_norm": w_exp * 0.15,
                "education_match": w_edu,
                "dense_similarity": w_sem * 0.7,
                "skill_recency": w_sem * 0.3,
            }
        else:
            self.weights = dict(DEFAULT_BASELINE_WEIGHTS)

        total_w = sum(self.weights.values()) or 1.0
        # Ensure weights normalize to 1.0
        self.weights = {k: v / total_w for k, v in self.weights.items()}

    def score(self, features: CandidateFeatureVector) -> CandidateScoreResult:
        """Compute score with exact additive feature contributions."""
        raw_vals: dict[str, float] = {
            "must_have_coverage": features.must_have_coverage.get_clamped_value(),
            "nice_to_have_coverage": features.nice_to_have_coverage.get_clamped_value(),
            "title_match": features.title_match.get_clamped_value(),
            "dense_similarity": features.dense_similarity.get_clamped_value(),
            "education_match": features.education_match.get_clamped_value(),
            "years_gap_norm": normalize_years_gap(features.years_gap.get_clamped_value()),
            "skill_recency": features.skill_recency.get_clamped_value(),
            "seniority_gap_norm": normalize_seniority_gap(
                features.seniority_gap.get_clamped_value()
            ),
        }

        missing_flags: dict[str, bool] = {
            "must_have_coverage": features.must_have_coverage.is_missing,
            "nice_to_have_coverage": features.nice_to_have_coverage.is_missing,
            "title_match": features.title_match.is_missing,
            "dense_similarity": features.dense_similarity.is_missing,
            "education_match": features.education_match.is_missing,
            "years_gap_norm": features.years_gap.is_missing,
            "skill_recency": features.skill_recency.is_missing,
            "seniority_gap_norm": features.seniority_gap.is_missing,
        }

        # Identify missing features and dynamically reweight
        active_weights: dict[str, float] = {}
        data_warnings: list[str] = []

        for name, is_miss in missing_flags.items():
            if not is_miss:
                active_weights[name] = self.weights.get(name, 0.0)
            else:
                data_warnings.append(f"Feature '{name}' is missing and reweighted.")

        sum_active = sum(active_weights.values())
        if sum_active > 0:
            normalized_active = {k: v / sum_active for k, v in active_weights.items()}
        else:
            normalized_active = {k: 1.0 / len(raw_vals) for k in raw_vals}

        total_score = 0.0
        contributions: list[FeatureContribution] = []

        for feat_name, val in raw_vals.items():
            is_miss = missing_flags.get(feat_name, False)
            weight = normalized_active.get(feat_name, 0.0) if not is_miss else 0.0
            contrib = val * weight
            total_score += contrib

            contributions.append(
                FeatureContribution(
                    feature_name=feat_name,
                    feature_value=round(val, 4),
                    contribution=round(contrib, 4),
                    percentage_of_score=0.0,  # Will compute below
                    is_missing=is_miss,
                )
            )

        final_score = float(np.clip(total_score, 0.0, 1.0))

        # Assign percentage of score
        for c in contributions:
            if final_score > 0:
                c.percentage_of_score = round((c.contribution / final_score) * 100.0, 1)

        # Average confidence across non-missing features
        feature_objs = [
            features.must_have_coverage,
            features.nice_to_have_coverage,
            features.title_match,
            features.dense_similarity,
            features.education_match,
            features.years_gap,
            features.skill_recency,
            features.seniority_gap,
        ]
        avg_conf = float(np.mean([f.confidence for f in feature_objs]))

        return CandidateScoreResult(
            resume_id=features.resume_id,
            job_id=features.job_id,
            final_score=round(final_score, 4),
            model_name="weighted_baseline",
            feature_contributions=contributions,
            base_value=0.0,
            overall_confidence=round(avg_conf, 2),
            data_missing_warnings=data_warnings,
        )


class MonotonicXGBoostScorer:
    """
    Gradient boosted trees trained with monotonic constraints:
    - More matched must-haves, higher coverage, or longer relevant tenure never lowers score.
    - More missing must-haves never raises score.
    """

    def __init__(self, model_path: str | None = None) -> None:
        self.model: Any = None
        if model_path:
            self.load(model_path)

    def train(
        self,
        x_train: np.ndarray,
        y_train: np.ndarray,
        params: dict[str, Any] | None = None,
    ) -> None:
        """Train XGBoost regressor with strict monotonic constraints."""
        import xgboost as xgb

        default_params: dict[str, Any] = {
            "n_estimators": 100,
            "max_depth": 3,
            "learning_rate": 0.05,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "monotone_constraints": str(MONOTONIC_CONSTRAINTS),
            "objective": "reg:squarederror",
            "random_state": 42,
        }
        if params:
            default_params.update(params)

        self.model = xgb.XGBRegressor(**default_params)
        self.model.fit(x_train, y_train)

    def score(self, features: CandidateFeatureVector) -> CandidateScoreResult:
        """Predict score using trained monotonic XGBoost model."""
        if self.model is None:
            raise RuntimeError("MonotonicXGBoostScorer model has not been trained or loaded.")

        x = features.to_numpy_array().reshape(1, -1)
        pred = float(self.model.predict(x)[0])
        final_score = float(np.clip(pred, 0.0, 1.0))

        # Compute feature importance / contribution
        # Use tree feature importances as baseline attribution
        importances = getattr(self.model, "feature_importances_", np.zeros(len(FEATURE_ORDER)))
        contributions: list[FeatureContribution] = []

        feature_dict = features.to_feature_dict()
        for idx, name in enumerate(FEATURE_ORDER):
            val = feature_dict.get(name, 0.0)
            imp = float(importances[idx]) if idx < len(importances) else 0.0
            contrib = val * imp
            contributions.append(
                FeatureContribution(
                    feature_name=name,
                    feature_value=round(val, 4),
                    contribution=round(contrib, 4),
                    percentage_of_score=round(imp * 100.0, 1),
                    is_missing=False,
                )
            )

        return CandidateScoreResult(
            resume_id=features.resume_id,
            job_id=features.job_id,
            final_score=round(final_score, 4),
            model_name="monotonic_xgboost",
            feature_contributions=contributions,
            base_value=0.0,
            overall_confidence=0.9,
            data_missing_warnings=[],
        )

    def save(self, path: str) -> None:
        """Save model to disk."""
        if self.model:
            self.model.save_model(path)

    def load(self, path: str) -> None:
        """Load model from disk."""
        import xgboost as xgb

        self.model = xgb.XGBRegressor()
        self.model.load_model(path)
