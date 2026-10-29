# RECRUIT LENS — FINAL RELEASE AUDIT REPORT (v1.0.0)

**Generated:** 2026-10-29 14:12:38 UTC
**Git Commit:** `2f10ae4756b5bd0cf0a9790a5ec87eb3a8c61bbb`
**Verification Script:** `scripts/generate_final_report.py`
**Report Integrity Standard:** All figures read strictly from verified disk artifacts; zero unmeasured claims.

---

## 1. Executive Summary & Quality Bars Verification

| Quality Gate / Standard | Threshold / Bar | Measured Value | Status | Artifact Citation |
| :--- | :--- | :--- | :--- | :--- |
| **Backend Test Pass Rate** | 100% Passing | 140/140 passed (0 failures, 0 errors) | **PASS** | `docs/pytest_results.xml:tests` |
| **Backend Statement Coverage** | $\ge 80.0\%$ | 89.21% (3853/4319 stmts) | **PASS** | `docs/coverage.json:totals.percent_covered` |
| **200-Resume Batch Execution** | $\le 300.0$ s | 289.16 s cold / 143.81 s warm | **PASS** | `docs/eval_benchmark_200.json:run_1_cold.total_wall_time_seconds` |
| **200-Resume Peak Memory** | $\le 400.0$ MB RSS | 317.4 MB cold / 313.8 MB warm | **PASS** | `docs/eval_benchmark_200.json:run_1_cold.peak_tree_rss_mb` |
| **Parser Holdout Fragments** | $< 5.0\%$ | 0.0% (0/130 rows) | **PASS** | `docs/eval_parser_dev30_fresh_measurement.json:metrics.fragments_rate_pct` |
| **Parser Duplicate Extractions** | 0 duplicates | 0 duplicates | **PASS** | `docs/eval_parser_dev30_fresh_measurement.json:metrics.duplicates_count` |
| **Parser Recoverable Rate** | $\ge 90.0\%$ | 96.3% (130/135 entries) | **PASS** | `docs/eval_parser_dev30_fresh_measurement.json:metrics.recoverable_rate_pct` |
| **Live Prompt Injection Defense**| 100.0% Neutralized | 100.0% (10/10 adversarial variants) | **PASS** | `docs/eval_injection_live.json:neutralization_rate_pct` |
| **Sanitizer False Alterations** | 0 of 200 real chunks | 0 altered chunks | **PASS** | `docs/eval_injection_live.json:sanitizer_real_chunks_tested.altered_chunks_count` |
| **Embedder Process Footprint** | $< 200.0$ MB RSS | 122.78 MB (MiniLM) / 140.5 MB (BGE) | **PASS** | `docs/eval_embedder_footprint_report.json:MiniLM-L6-v2-quantized.loaded_rss_mb` |
| **Embedder Latency** | $< 10.0$ ms / chunk | 3.3 ms / chunk | **PASS** | `docs/eval_embedder_footprint_report.json:MiniLM-L6-v2-quantized.inference_latency_ms_per_chunk` |
| **Scoring Model Marginal Gain** | $> 0.0$ vs heuristic | Spearman +0.0897 / NDCG@10 +0.0725 | **PASS** | `docs/eval_scoring_validity_report.json:marginal_gains.spearman_rho_gain` |
| **Drift Monitoring (PSI)** | $< 0.10$ (stable) | 0.0247 (Drift detected: False) | **PASS** | `docs/eval_model_retrain_report.json:drift_monitoring.population_stability_index` |
| **Secret Leaks (Gitleaks)** | 0 leaks in history | 0 leaks detected across full git log | **PASS** | `gitleaks git --verbose` |
| **Known Vulnerabilities** | 0 vulnerabilities | 0 vulnerabilities (`pip-audit 2.10.1`) | **PASS** | `docs/SECURITY.md` |

---

## 2. Component Deliverables

### A. Core Backend Engine
- **Deterministic Multi-Stage Parsing:** Rule-of-three layout segmenter, strict regex/rule-based experience & date extractor (`pdf_parser.py`, `experience_extractor.py`), zero LLM in scoring logic.
- **Fast Isolated Embedder:** Quantized ONNX MiniLM-L6-v2 consuming only 122.78 MB RSS with 3.3 ms inference latency per chunk.
- **Hybrid Retrieval:** Multi-field BM25s + cosine semantic similarity with candidate isolation.
- **Explainable Monotonic Scoring:** 12-feature XGBoost regressor enforcing positive monotonicity constraints for experience and skill coverage, preventing bias gaming.

### B. Recruiter Portal (17 Screens)
- Built with Tailwind CSS, Lucide icons, Recharts, and strict TypeScript.
- **Journey Screens:**
  1. Login Screen (with demo credentials banner)
  2. Dashboard Command Center
  3. Job Requisition Creation
  4. Requirements Confirmation Modal
  5. Bulk Resume Upload (magic bytes & 15MB limit)
  6. Batch Progress Indicator
  7. Ranked Candidates Table (strict company omission, tier badges)
  8. Candidate Detail Dossier (what-if simulator, verified timeline)
  9. Interview Questions Rubric Modal
  10. Grounded Copilot Q&A (hybrid citations, "not found" rule)
  11. Candidate Comparison Matrix (side-by-side across 2-3 candidates)
  12. Recruiter Decision Modal (with mandatory audit notes)
  13. Email Center (safe dry-run mode, draft vs edited status)
  14. Post-Interview Scorecard Modal
  15. Hiring Pipeline Board (interactive Kanban)
  16. Recruitment Analytics & Reports Screen (Recharts funnel & agreement)
  17. Settings, Exports & Immutable Audit Trail Screen
- Tested via Playwright headless Chromium e2e suite and Vitest unit tests (6/6 passing).

### C. Security, Safety & Resilience
- **Grounded Copilot (`app/llm/copilot.py`):** Answers recruiter questions exclusively from candidate evidence chunks. Automatically replies `"Information not found in this resume."` if query concepts are absent.
- **End-to-End Blind Mode (`app/llm/guardrails.py`):** Automatically redacts names, emails, phones, DOB, street addresses, gender pronouns, and universities before prompting.
- **Official Python SDK MCP Server (`app/mcp/server.py`):** Exposes read-only tools and gates stage transition mutations with single-use confirmation tokens (`McpConfirmationToken`).
- **Resilience Suite (`tests/test_resilience.py`):** Verified recovery under LLM downtime, quota exhaustion, corrupt PDF uploads, and 100-page documents.

---

## 3. Retraction of Previous Unmeasured Claims
In compliance with Rule 12:
1. Retracted heuristic claim of "98% structured titles" — replaced with ground truth measurement on DEV Set 2: 96.3% recoverable titles (`docs/eval_parser_dev30_fresh_measurement.json:metrics.recoverable_rate_pct`).
2. Retracted monolithic process RSS figure of 363.3 MB — replaced with isolated subprocess measurement of 122.78 MB (`docs/eval_embedder_footprint_report.json:MiniLM-L6-v2-quantized.loaded_rss_mb`).
3. Retracted self-graded 40-resume audit claim from pass/fail status (`docs/eval_parser_audit_40_report.json:metrics.clean_correct_entries`).

---

## 4. Attributions & Licensing
- **License:** MIT License (permissive open-source).
- **Taxonomy Attribution:** This product includes skills and occupation taxonomies derived from O*NET 28.0, sponsored by the U.S. Department of Labor, Employment and Training Administration (USDOL/ETA), used under the Creative Commons Attribution 4.0 International (CC BY 4.0) license.
