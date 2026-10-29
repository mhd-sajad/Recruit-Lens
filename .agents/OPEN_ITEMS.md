# BATCH 4 CLOSE-OUT — OPEN ITEMS

Saved from user request on 2026-10-29.

## STEP 0: HAND ME THE HOLDOUT FILE (do this first, before any code change)
- [x] Run `ls -l data/parser_holdout_30_fresh.csv` and print the output. If the file does not exist, create it now from 30 resumes in data/resumes_sample_300 that are in none of these sets: the first-100 set, the 40-resume audit set, the 30 dev resumes (data/parser_holdout_30.csv). Print the three ID lists you excluded. Use a fixed seed and the CURRENT parser.
- [x] Columns exactly as in parser_holdout_30.csv: resume_id, raw_experience_lines (cap at 300 characters), extracted_title, extracted_company, start_date, end_date. No classification column and no heuristic column.
- [x] Write data/parser_holdout_30_fresh.meta.txt with the git commit hash of the parser, the row count, the resume IDs and the sha256 of the CSV. Do not regenerate or edit the CSV after this step.
- [x] Copy this one CSV to ~/recruit_lens_review/parser_holdout_30_fresh.csv (create the folder if needed). I explicitly authorize this one copy outside the repo and nothing else. Print its absolute path, row count and sha256.
- [x] The CSV contains resume text. Confirm with `git check-ignore -v` that it is ignored, and never commit or push it.

## RULES (add to .agents/AGENTS.md)
- [x] A metric must measure the thing it names. A number computed from the reviewer's labels, or graded by your own keyword lists, is not a measurement of the parser. Label self-graded numbers "self-graded" and never put them in a pass/fail table.
- [x] Every figure in a report comes from a saved file with file:key, and make_report.py exits non-zero on any missing key.
- [x] Test counts come from saved pytest output (junit xml), never from coverage.json.
- [x] No feature or test without a requirement in docs/SPEC.md. Do not add webhooks or roles the SPEC does not have.

## GATE A: REPORT INTEGRITY (stop if not met)
- [x] A.1: Replace dev_set_holdout_30 clean/fragment with real measurement against reviewer labels (docs/eval_parser_dev30_measurement.json)
- [x] A.2: Remove 40-resume audit "96.48% clean" from pass/fail tables; report row-count change as fact (docs/eval_parser_audit_40_report.json)
- [x] A.3: Explain MiniLM RSS 363.3 MB vs earlier measurements; fix or restate cap (docs/eval_embedder_footprint_report.json)
- [x] A.4: Test counts from saved pytest output (docs/pytest_results.xml); map "7 owed security tests" to SPEC requirements; remove tests with no requirement (webhook signature test removed)

## GATE B: PERFORMANCE (stop if not met)
- [x] Explain 225.91s/375.2MB vs 342.55s/447.4MB difference (docs/eval_benchmark_200.json:explanation_variance)
- [x] Run 200-resume benchmark 3 times (median 125.04s, 349.3 MB peak RSS)
- [x] Bars: ≤300s wall time (125.04s, PASS) and ≤400MB RSS (349.3 MB, PASS)
- [x] Use process pool for PDF parsing (2 workers), per-file timeouts, cache parse results, embed in streamed batches, release page objects

## GATE C: ROUTER TESTS
- [x] Every router module at ≥70% coverage (docs/eval_router_modules_coverage.json: all 94.0%–100.0%)
- [x] Named tests for: isolation, state transitions, email send gates, CSV injection, hard delete, data export, what-if, SSE progress/cancel, upload limits, login throttling, refresh reuse (backend/tests/test_router_modules_coverage.py)
- [x] Save per-module coverage (docs/eval_router_modules_coverage.json)

## GATE D: RETRIEVAL
- [x] D.1: List dropped gold pairs (3 pairs listed); add confidence intervals at N=31 (docs/eval_corpus_retrieval_report.json)
- [x] D.2: Print full corpus-wide and within-resume table (docs/eval_corpus_retrieval_report.json)
- [x] D.3: Regression analysis vs old project; old vs new chunker control experiment (docs/retrieval_control_experiment.json)
- [x] D.4: Count mojibake chunks; apply ftfy+placeholder cleaning before chunking (docs/eval_chunker_cleanliness.json: 994 -> 0)
- [x] D.5: Vocabulary-mismatch table with BM25 vs dense/hybrid comparison (docs/eval_vocabulary_mismatch.json)

## GATE E: SCORING VALIDITY
- [x] Re-run weak labels, training, tiers on cleaned parser + expanded taxonomy
- [x] Print from saved files: Spearman, tier thresholds, per-role-family, per-category taxonomy coverage, years_gap and title_match before/after parser change (docs/eval_scoring_validity_report.json, docs/taxonomy_coverage_report.json)

## GATE F: CRITIC AND INJECTION
- [x] F.1: Report upper bound for 0/60 false accepts or extend to 150 sentences (Rule of Three 5.0% at N=60, 2.0% at N=150, docs/eval_critic_calibration.json)
- [x] F.2: Per-variant injection recording (10 variants including Spanish, German, and split-across-chunks, docs/eval_injection_live.json)
- [x] F.3: Do not change critic threshold until reviewer labels come back (tau=0.40 maintained)

## GATE G: MODEL COMPARISON AND LATENCY
- [x] Compare qwen, gpt-oss-20b, gpt-oss-120b on same 20 candidates with real prompts (docs/eval_model_comparison_report.json)
- [x] Critic-checked pass rate, latency, tokens, TPM/RPM limits (docs/eval_model_comparison_report.json)

## GATE H: BATCH 4 EVIDENCE
- [x] Postgres test and Alembic migration against Supabase (scripts/test_postgres_connection.py, PostgreSQL 18.6, alembic head eab4a0bfbd5a)
- [x] OpenAPI route list, response headers, rate limits, /ready, /metrics (app.openapi().paths: 32 endpoints)
- [x] CI run IDs for branch, main, tags v0.5.1–v0.5.3 recorded in reports
