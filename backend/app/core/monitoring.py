"""
Evaluation tracking, model monitoring, and drift detection module for Recruit Lens.

Implements:
1. Population Stability Index (PSI) calculation across binned score distributions.
2. Kolmogorov-Smirnov (KS) two-sample distribution drift testing.
3. Database persistence for evaluation runs and drift metrics.
"""

from typing import Any

import numpy as np
from scipy import stats
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import EvalRunRecord
from app.logging import get_logger

logger = get_logger("core.monitoring")


def compute_psi(
    baseline_scores: list[float] | np.ndarray,
    current_scores: list[float] | np.ndarray,
    num_bins: int = 10,
    epsilon: float = 1e-4,
) -> float:
    """
    Calculate Population Stability Index (PSI) between baseline and incoming score distributions.

    Interpretation thresholds:
    - PSI < 0.10: No significant distribution change / stable.
    - 0.10 <= PSI < 0.25: Slight drift detected / monitor closely.
    - PSI >= 0.25: Significant drift / model retraining recommended.
    """
    b = np.asarray(baseline_scores, dtype=float)
    c = np.asarray(current_scores, dtype=float)

    if len(b) == 0 or len(c) == 0:
        return 0.0

    # Determine bin edges from baseline percentiles
    quantiles = np.linspace(0, 100, num_bins + 1)
    bin_edges = np.percentile(b, quantiles)
    # Ensure strictly monotonic bin edges
    bin_edges = np.unique(bin_edges)
    if len(bin_edges) < 2:
        return 0.0

    # Bin frequencies
    b_counts, _ = np.histogram(b, bins=bin_edges)
    c_counts, _ = np.histogram(c, bins=bin_edges)

    # Convert to proportions with smoothing epsilon
    b_props = (b_counts + epsilon) / (len(b) + epsilon * len(b_counts))
    c_props = (c_counts + epsilon) / (len(c) + epsilon * len(c_counts))

    psi_val = np.sum((c_props - b_props) * np.log(c_props / b_props))
    return float(max(0.0, psi_val))


def compute_ks_drift(
    baseline_scores: list[float] | np.ndarray,
    current_scores: list[float] | np.ndarray,
) -> dict[str, Any]:
    """
    Calculate Kolmogorov-Smirnov two-sample test for statistical drift detection.
    Rejects null hypothesis of identical distributions when p_value < 0.05.
    """
    b = np.asarray(baseline_scores, dtype=float)
    c = np.asarray(current_scores, dtype=float)

    if len(b) < 2 or len(c) < 2:
        return {
            "statistic": 0.0,
            "p_value": 1.0,
            "drift_detected": False,
        }

    res = stats.ks_2samp(b, c)
    return {
        "statistic": round(float(res.statistic), 4),
        "p_value": round(float(res.pvalue), 6),
        "drift_detected": bool(res.pvalue < 0.05),
    }


async def record_eval_run_in_db(
    session: AsyncSession,
    run_name: str,
    model_version: str,
    dataset_name: str,
    metrics: dict[str, Any],
    drift_metrics: dict[str, Any] | None = None,
    notes: str = "",
) -> EvalRunRecord:
    """Persist an evaluation run and its drift metrics into PostgreSQL / SQLite database."""
    record = EvalRunRecord(
        run_name=run_name,
        model_version=model_version,
        dataset_name=dataset_name,
        metrics_json=metrics,
        drift_metrics_json=drift_metrics or {},
        notes=notes,
    )
    session.add(record)
    await session.commit()
    logger.info("Persisted EvalRunRecord %s for model version %s", record.id, model_version)
    return record


async def get_recent_eval_runs(session: AsyncSession, limit: int = 20) -> list[EvalRunRecord]:
    """Retrieve recent evaluation and monitoring runs ordered by creation date."""
    stmt = select(EvalRunRecord).order_by(EvalRunRecord.created_at.desc()).limit(limit)
    res = await session.execute(stmt)
    return list(res.scalars().all())
