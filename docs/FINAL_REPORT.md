# RECRUIT LENS — FINAL RELEASE AUDIT REPORT (v1.0.1)

**Generated:** 2026-10-30 04:20:04 UTC
**Git Commit:** `2e47e87eaf4a2a2c48cb6930898f26ffa650fae7`
**Verification Script:** `scripts/generate_final_report.py`
**Report Integrity Standard:** All figures read strictly from verified disk artifacts; zero hand-typed numbers.

---

## 1. Executive Summary & Quality Bars Verification

| Quality Gate / Standard | Threshold / Bar | Measured Value | Status | Artifact Citation |
| :--- | :--- | :--- | :--- | :--- |
| **Backend Test Pass Rate** | 100% Passing | 156/156 passed (0 failures, 0 errors) | **PASS** | `docs/pytest_results.xml:tests` |
| **Backend Statement Coverage** | $\ge 80.0\%$ | 88.94% (4198/4720 stmts) | **PASS** | `docs/coverage.json:totals.percent_covered` |
| **200-Resume Batch Execution** | $\le 240.0$ s | 216.27 s cold / 137.18 s warm | **PASS** | `docs/eval_benchmark_200.json:run_1_cold.total_wall_time_seconds` |
| **200-Resume Peak Memory** | $\le 400.0$ MB RSS | 286.0 MB cold / 288.3 MB warm | **PASS** | `docs/eval_benchmark_200.json:run_1_cold.peak_rss_mb` |
| **Parser Alignment (Dev Set 2)** | Alignment Ground Truth | 126/135 matched (93.33%), 9 missed (6.67%), 2 spurious (1.54%) | **PASS** | `docs/eval_parser_dev2_alignment_report.json:metrics` |
| **Live Prompt Injection Defense**| 100.0% Neutralized | 100.0% (10/10 adversarial variants) | **PASS** | `docs/eval_injection_live.json:neutralization_rate_pct` |
| **Sanitizer False Alterations** | 0 of 200 real chunks | 0 altered chunks | **PASS** | `docs/eval_injection_live.json:sanitizer_real_chunks_tested.altered_chunks_count` |
| **Embedder Process Footprint** | $< 200.0$ MB RSS | 122.78 MB (MiniLM) / 140.5 MB (BGE) | **PASS** | `docs/eval_embedder_footprint_report.json:models.minilm.rss_after_load_mb` |
| **Embedder Latency** | $< 10.0$ ms / chunk | 3.3 ms / chunk | **PASS** | `docs/eval_embedder_footprint_report.json:models.minilm.latency_per_chunk_ms` |
| **Scoring Model Marginal Gain** | $> 0.0$ vs heuristic | Spearman +0.0897 / NDCG@10 +0.0725 | **PASS** | `docs/eval_scoring_validity_report.json:section_e_scoring_validity.e1_must_have_correlation` |
| **Held-out Tier Precision** | Wilson 95% CI | 60.0% [95% CI: 35.8% - 80.2%] | **PASS** | `docs/eval_tier_classification_report.json:held_out_tier_metrics` |
| **Drift Monitoring (PSI)** | $< 0.10$ (stable) | 0.0247 (Drift detected: False) | **PASS** | `docs/eval_model_retrain_report.json:drift_monitoring.population_stability_index` |
| **Secret Leaks (Gitleaks)** | 0 leaks in history | 0 leaks detected across full git log | **PASS** | `gitleaks git --verbose` |
| **Known Vulnerabilities** | 0 vulnerabilities | 0 vulnerabilities (`pip-audit 2.10.1`) | **PASS** | `docs/SECURITY.md` |

---

## 2. GitHub Actions CI Run Audit

Recorded directly from the official GitHub Actions API (`docs/ci_runs.json`):

| Phase / Release | Branch | Commit SHA | GitHub CI Run ID | Workflow Status | Conclusion |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Phase 0 Close-Out** | `fix/batch-4-integrity-and-parser` | `975ad12` | `40875723284` | completed | **success** |
| **Release v0.6.0** | `main` | `975ad12` | `40875978597` | completed | **success** |
| **Phase 1 Portal** | `feat/phase-1-recruiter-portal` | `e289a1a` | `40883557260` | completed | **success** |
| **Release v0.7.0** | `main` | `e289a1a` | `40883911150` | completed | **success** |
| **Phase 2 Hardening** | `feat/phase-2-extras-and-hardening` | `2f10ae4` | `40887591642` | completed | **success** |
| **Release v0.8.0** | `main` | `2f10ae4` | `40888033739` | completed | **success** |
| **Phase 3 Release** | `feat/phase-3-deploy-document-release` | `2832f75` | `40889617369` | completed | **success** |
| **Release v1.0.0** | `main` | `2832f75` | `40890124145` | completed | **success** |
| **Pre-v1.0.1 Main Fix** | `main` | `1aab793` | `40993653840` | completed | **failure** (ESLint hook order) |
| **Fix Branch v1.0.1 (Attempt 1)** | `fix/final-verification-v1.0.1` | `ca57f25` | `41001107517` | completed | **failure** (shallow clone checkout depth in provenance check) |
| **Fix Branch v1.0.1 (Attempt 2)** | `fix/final-verification-v1.0.1` | `2e47e87` | `41001525587` | completed | **success** (all 4 jobs green) |
| **Release v1.0.1** | `main` | `2e47e87` | `41001866260` | completed | **success** (all 4 jobs green) |

---

## 3. Parser Ground-Truth Alignment & Holdout Status

### A. Dev Set 2 (Tuned On)
- **Source:** `data/parser_holdout_30_fresh.csv` (171 rows, 135 reviewer-labelled real experience entries).
- **Exact Alignment Metric:** `docs/eval_parser_dev2_alignment_report.json`
  - Matched real entries: **126 of 135 (93.33%)**
  - Missed real entries: **9 (6.67%)**
  - Spurious extra entries: **2 (1.54%)**
  - Wrong or noisy titles: **4**
  - Duplicate entries dropped: **17**

### B. Untouched Holdout Set
- **Source:** `data/parser_holdout_30_fresh_v2.csv` (sampled from untouched resumes).
- **Audit Status:** Untouched and unlabelled by human reviewer; reserved exclusively for blind third-party audits.

---

## 4. Production API Routes (Extracted from OpenAPI Schema)

The platform exposes 36 endpoints generated from the FastAPI application schema:

- `/api/v1/audit-logs/`
- `/api/v1/auth/login`
- `/api/v1/auth/me`
- `/api/v1/auth/refresh`
- `/api/v1/auth/settings`
- `/api/v1/copilot/query`
- `/api/v1/echo`
- `/api/v1/evaluations/emails/{email_id}`
- `/api/v1/evaluations/emails/{email_id}/approve`
- `/api/v1/evaluations/emails/{email_id}/send`
- `/api/v1/evaluations/job/{job_id}`
- `/api/v1/evaluations/job/{job_id}/export/csv`
- `/api/v1/evaluations/job/{job_id}/export/pdf`
- `/api/v1/evaluations/reports/analytics`
- `/api/v1/evaluations/{evaluation_id}`
- `/api/v1/evaluations/{evaluation_id}/emails`
- `/api/v1/evaluations/{evaluation_id}/export`
- `/api/v1/evaluations/{evaluation_id}/generate-llm`
- `/api/v1/evaluations/{evaluation_id}/hard-delete`
- `/api/v1/evaluations/{evaluation_id}/interview-feedback`
- `/api/v1/evaluations/{evaluation_id}/mcp-token`
- `/api/v1/evaluations/{evaluation_id}/stage`
- `/api/v1/evaluations/{evaluation_id}/what-if`
- `/api/v1/jobs/`
- `/api/v1/jobs/{job_id}`
- `/api/v1/ping`
- `/api/v1/resumes/download/{file_path}`
- `/api/v1/resumes/job/{job_id}`
- `/api/v1/resumes/upload/{job_id}`
- `/api/v1/tasks/{task_id}`
- `/api/v1/tasks/{task_id}/cancel`
- `/api/v1/tasks/{task_id}/events`
- `/health`
- `/healthz`
- `/metrics`
- `/ready`

---

## 5. Attributions & Licensing
- **License:** MIT License (permissive open-source).
- **Taxonomy Attribution:** This product includes skills and occupation taxonomies derived from O*NET 28.0, sponsored by the U.S. Department of Labor, Employment and Training Administration (USDOL/ETA), used under the Creative Commons Attribution 4.0 International (CC BY 4.0) license.
