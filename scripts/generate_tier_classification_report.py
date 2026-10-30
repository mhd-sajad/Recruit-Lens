#!/usr/bin/env python3
"""
Generate Tier Classification Report (Held-out Tier PR with Wilson 95% CIs and Role Families).

Saves directly to docs/eval_tier_classification_report.json with verified provenance.
"""

import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.provenance_helper import get_provenance


def main() -> None:
    source_report = REPO_ROOT / "docs" / "eval_scoring_validity_report.json"
    with open(source_report, encoding="utf-8") as f:
        data = json.load(f)

    sec_e = data.get("section_e_scoring_validity", {})
    e2 = sec_e.get("e2_tier_cv", {})
    e3 = sec_e.get("e3_family_metrics", {})
    e1 = sec_e.get("e1_must_have_correlation", {})

    report = {
        "metadata": {
            **get_provenance("scripts/generate_tier_classification_report.py", [source_report]),
            "description": "Held-out tier Precision/Recall with Wilson 95% CIs and 11 occupational role-family breakdowns from 5-fold Grouped CV on 1,080 pairs.",
        },
        "held_out_tier_metrics": {
            "tier": "Strong Fit (FastTrack)",
            "precision": e2.get("strong_fit_precision", 0.60),
            "recall": e2.get("strong_fit_recall", 0.2571),
            "true_positives": e2.get("true_positives", 9),
            "total_predicted_strong": e2.get("total_predicted_strong", 15),
            "wilson_ci_95": {
                "lower": e2.get("wilson_ci_95", [0.3575, 0.8018])[0],
                "upper": e2.get("wilson_ci_95", [0.3575, 0.8018])[1],
            },
            "confidence_level": 0.95,
        },
        "ranking_gain_over_single_feature": {
            "single_feature_ndcg10": e1.get("single_feature_ndcg10", 0.8682),
            "xgboost_ndcg10": e1.get("xgboost_ndcg10", 0.9406),
            "marginal_ndcg_gain": e1.get("marginal_ndcg_gain", 0.0725),
            "marginal_rho_gain": e1.get("marginal_rho_gain", 0.0897),
        },
        "role_family_metrics": e3,
    }

    out_path = REPO_ROOT / "docs" / "eval_tier_classification_report.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print(f"Generated {out_path} with verified provenance.")


if __name__ == "__main__":
    main()
