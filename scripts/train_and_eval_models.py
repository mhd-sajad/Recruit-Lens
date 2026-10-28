"""
Model Comparison and Grouped Cross-Validation: Weighted Baseline vs Monotonic XGBoost

Performs 5-fold GroupKFold CV grouped by resume_id to prevent candidate leakage.
Computes:
- NDCG@5 and NDCG@10
- Spearman rank correlation (rho)
- MAE and RMSE
- Expected Calibration Error (ECE)

Decision Rule:
Keep XGBoost only if it beats the baseline by a clear margin; otherwise ship the baseline.
"""

import json
import logging
from pathlib import Path

import numpy as np
from app.core.features import CandidateFeatureVector, FeatureValue
from app.core.scoring import (
    FEATURE_ORDER,
    MonotonicXGBoostScorer,
    WeightedBaselineScorer,
)
from scipy.stats import spearmanr
from sklearn.metrics import ndcg_score
from sklearn.model_selection import GroupKFold

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("model_eval")


def compute_ece(y_true: np.ndarray, y_pred: np.ndarray, n_bins: int = 10) -> float:
    """Compute Expected Calibration Error (ECE) across probability/score bins."""
    bins = np.linspace(0.0, 1.0, n_bins + 1)
    ece = 0.0
    total_samples = len(y_true)

    for i in range(n_bins):
        bin_mask = (y_pred >= bins[i]) & (y_pred < bins[i + 1])
        if np.sum(bin_mask) > 0:
            bin_acc = np.mean(y_true[bin_mask])
            bin_conf = np.mean(y_pred[bin_mask])
            bin_weight = np.sum(bin_mask) / total_samples
            ece += bin_weight * abs(bin_acc - bin_conf)

    return float(ece)


def dict_to_feature_vector(
    feat_dict: dict[str, float], resume_id: str, job_id: str
) -> CandidateFeatureVector:
    """Helper to reconstruct CandidateFeatureVector from dict for baseline scoring."""

    def make_fv(name: str, val: float, mi: float, ma: float) -> FeatureValue:
        return FeatureValue(
            name=name,
            value=val,
            confidence=1.0,
            is_missing=False,
            min_bound=mi,
            max_bound=ma,
        )

    return CandidateFeatureVector(
        resume_id=resume_id,
        job_id=job_id,
        must_have_coverage=make_fv(
            "must_have_coverage", feat_dict.get("must_have_coverage", 0.0), 0.0, 1.0
        ),
        nice_to_have_coverage=make_fv(
            "nice_to_have_coverage",
            feat_dict.get("nice_to_have_coverage", 0.0),
            0.0,
            1.0,
        ),
        matched_must_count=make_fv(
            "matched_must_count", feat_dict.get("matched_must_count", 0.0), 0.0, 50.0
        ),
        matched_nice_count=make_fv(
            "matched_nice_count", feat_dict.get("matched_nice_count", 0.0), 0.0, 50.0
        ),
        inferred_count=make_fv("inferred_count", feat_dict.get("inferred_count", 0.0), 0.0, 50.0),
        missing_must_count=make_fv(
            "missing_must_count", feat_dict.get("missing_must_count", 0.0), 0.0, 50.0
        ),
        years_gap=make_fv("years_gap", feat_dict.get("years_gap", 0.0), -10.0, 15.0),
        seniority_gap=make_fv("seniority_gap", feat_dict.get("seniority_gap", 0.0), -4.0, 4.0),
        education_match=make_fv("education_match", feat_dict.get("education_match", 0.0), 0.0, 1.0),
        title_match=make_fv("title_match", feat_dict.get("title_match", 0.0), 0.0, 1.0),
        skill_recency=make_fv("skill_recency", feat_dict.get("skill_recency", 0.0), 0.0, 1.0),
        dense_similarity=make_fv(
            "dense_similarity", feat_dict.get("dense_similarity", 0.0), 0.0, 1.0
        ),
    )


def evaluate_predictions(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    job_ids: list[str],
) -> dict[str, float]:
    """Calculate ranking and calibration metrics across grouped job queries."""
    # 1. Global regression and calibration metrics
    mae = float(np.mean(np.abs(y_true - y_pred)))
    rmse = float(np.sqrt(np.mean((y_true - y_pred) ** 2)))
    ece = compute_ece(y_true, y_pred)
    spearman, _ = spearmanr(y_true, y_pred)

    # 2. Per-job NDCG ranking metrics
    unique_jobs = list(set(job_ids))
    ndcg_5_list: list[float] = []
    ndcg_10_list: list[float] = []

    for jid in unique_jobs:
        indices = [idx for idx, j in enumerate(job_ids) if j == jid]
        if len(indices) >= 3:
            y_t_job = y_true[indices].reshape(1, -1)
            y_p_job = y_pred[indices].reshape(1, -1)
            try:
                # Require non-zero variance in true scores for NDCG
                if np.std(y_t_job) > 1e-6:
                    ndcg_5 = float(ndcg_score(y_t_job, y_p_job, k=min(5, len(indices))))
                    ndcg_10 = float(ndcg_score(y_t_job, y_p_job, k=min(10, len(indices))))
                    ndcg_5_list.append(ndcg_5)
                    ndcg_10_list.append(ndcg_10)
            except ValueError as e:
                logger.debug("NDCG calculation skipped for job %s: %s", jid, e)

    return {
        "ndcg@5": float(np.mean(ndcg_5_list)) if ndcg_5_list else 0.0,
        "ndcg@10": float(np.mean(ndcg_10_list)) if ndcg_10_list else 0.0,
        "spearman_rho": float(spearman) if not np.isnan(spearman) else 0.0,
        "mae": round(mae, 4),
        "rmse": round(rmse, 4),
        "ece": round(ece, 4),
    }


def main() -> None:
    data_path = Path("data/weak_supervision_pairs.json")
    if not data_path.exists():
        logger.error(
            "Dataset not found at %s. Run scripts/build_weak_supervision.py first.",
            data_path,
        )
        return

    logger.info("Loading weak supervision dataset from %s...", data_path)
    with open(data_path, encoding="utf-8") as f:
        data = json.load(f)

    pairs = data["pairs"]
    logger.info(
        "Loaded %d pairs across %d total candidates.",
        len(pairs),
        data["metadata"]["total_candidates"],
    )

    # Prepare matrix inputs
    x_matrix = np.zeros((len(pairs), len(FEATURE_ORDER)), dtype=np.float32)
    y_vector = np.zeros(len(pairs), dtype=np.float32)
    resumes: list[str] = []
    jobs: list[str] = []
    feature_vectors: list[CandidateFeatureVector] = []

    for i, p in enumerate(pairs):
        f_dict = p["features"]
        for j, k in enumerate(FEATURE_ORDER):
            x_matrix[i, j] = f_dict.get(k, 0.0)
        y_vector[i] = float(p["target_score"])
        resumes.append(p["resume_id"])
        jobs.append(p["job_id"])
        feature_vectors.append(dict_to_feature_vector(f_dict, p["resume_id"], p["job_id"]))

    # 5-fold GroupKFold by resume_id
    gkf = GroupKFold(n_splits=5)
    baseline_scorer = WeightedBaselineScorer()

    xgb_metrics_list: list[dict[str, float]] = []
    base_metrics_list: list[dict[str, float]] = []

    logger.info("Starting 5-fold GroupKFold cross-validation (grouped by resume_id)...")
    for fold, (train_idx, val_idx) in enumerate(gkf.split(x_matrix, y_vector, groups=resumes), 1):
        x_tr, y_tr = x_matrix[train_idx], y_vector[train_idx]
        x_va, y_va = x_matrix[val_idx], y_vector[val_idx]
        val_jobs = [jobs[idx] for idx in val_idx]

        # 1. Evaluate Weighted Baseline on validation set
        base_preds = np.array(
            [baseline_scorer.score(feature_vectors[idx]).final_score for idx in val_idx],
            dtype=np.float32,
        )
        base_eval = evaluate_predictions(y_va, base_preds, val_jobs)
        base_metrics_list.append(base_eval)

        # 2. Train and evaluate Monotonic XGBoost
        xgb_scorer = MonotonicXGBoostScorer()
        xgb_scorer.train(x_tr, y_tr)
        xgb_preds = np.array(
            [
                float(xgb_scorer.model.predict(x_va[row_i].reshape(1, -1))[0])
                for row_i in range(len(val_idx))
            ],
            dtype=np.float32,
        )
        xgb_preds = np.clip(xgb_preds, 0.0, 1.0)
        xgb_eval = evaluate_predictions(y_va, xgb_preds, val_jobs)
        xgb_metrics_list.append(xgb_eval)

        logger.info(
            "Fold %d: Baseline NDCG@10=%.4f (Rho=%.4f) | XGBoost NDCG@10=%.4f (Rho=%.4f)",
            fold,
            base_eval["ndcg@10"],
            base_eval["spearman_rho"],
            xgb_eval["ndcg@10"],
            xgb_eval["spearman_rho"],
        )

    # Average metrics
    avg_base = {k: float(np.mean([m[k] for m in base_metrics_list])) for k in base_metrics_list[0]}
    avg_xgb = {k: float(np.mean([m[k] for m in xgb_metrics_list])) for k in xgb_metrics_list[0]}

    logger.info("=== 5-Fold GroupKFold Cross-Validation Results ===")
    logger.info(
        "Weighted Baseline: NDCG@5=%.4f | NDCG@10=%.4f | Rho=%.4f | MAE=%.4f | RMSE=%.4f | ECE=%.4f",
        avg_base["ndcg@5"],
        avg_base["ndcg@10"],
        avg_base["spearman_rho"],
        avg_base["mae"],
        avg_base["rmse"],
        avg_base["ece"],
    )
    logger.info(
        "Monotonic XGBoost: NDCG@5=%.4f | NDCG@10=%.4f | Rho=%.4f | MAE=%.4f | RMSE=%.4f | ECE=%.4f",
        avg_xgb["ndcg@5"],
        avg_xgb["ndcg@10"],
        avg_xgb["spearman_rho"],
        avg_xgb["mae"],
        avg_xgb["rmse"],
        avg_xgb["ece"],
    )

    # Decision logic
    ndcg_delta = avg_xgb["ndcg@10"] - avg_base["ndcg@10"]
    rho_delta = avg_xgb["spearman_rho"] - avg_base["spearman_rho"]

    decision_to_keep_xgb = (ndcg_delta >= 0.03) or (rho_delta >= 0.03)
    winning_model = "monotonic_xgboost" if decision_to_keep_xgb else "weighted_baseline"

    logger.info("NDCG@10 Delta (XGB - Base): %+.4f", ndcg_delta)
    logger.info("Spearman Rho Delta (XGB - Base): %+.4f", rho_delta)
    logger.info(
        "Decision: Ship %s (Clear margin criteria: >= 0.03 delta; met = %s)",
        winning_model.upper(),
        decision_to_keep_xgb,
    )

    # Train final full model and save weights
    final_xgb = MonotonicXGBoostScorer()
    final_xgb.train(x_matrix, y_vector)
    model_save_path = "backend/app/data/scoring_xgb.json"
    final_xgb.save(model_save_path)
    logger.info("Saved trained XGBoost model to %s", model_save_path)

    # Save benchmark report to docs/eval_scoring_comparison.json
    output_report = {
        "metadata": {
            "cv_method": "5-Fold GroupKFold (grouped by resume_id)",
            "total_pairs": len(pairs),
            "total_candidates": data["metadata"]["total_candidates"],
            "winning_model": winning_model,
            "decision_rule": "Keep XGBoost only if it beats baseline by >= 0.03 NDCG@10 or Spearman Rho",
        },
        "baseline_metrics": avg_base,
        "xgboost_metrics": avg_xgb,
        "deltas": {
            "ndcg_10_delta": round(ndcg_delta, 4),
            "spearman_rho_delta": round(rho_delta, 4),
            "mae_delta": round(avg_xgb["mae"] - avg_base["mae"], 4),
        },
    }

    report_path = Path("docs/eval_scoring_comparison.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(output_report, f, indent=2)
    logger.info("Saved comparison report to %s", report_path)


if __name__ == "__main__":
    main()
