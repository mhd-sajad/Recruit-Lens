# BATCH 4 CLOSE-OUT — OPEN ITEMS

Saved from user request on 2026-10-29.

## STEP 0: HAND ME THE HOLDOUT FILE (do this first, before any code change)
- [ ] Run `ls -l data/parser_holdout_30_fresh.csv` and print the output. If the file does not exist, create it now from 30 resumes in data/resumes_sample_300 that are in none of these sets: the first-100 set, the 40-resume audit set, the 30 dev resumes (data/parser_holdout_30.csv). Print the three ID lists you excluded. Use a fixed seed and the CURRENT parser.
- [ ] Columns exactly as in parser_holdout_30.csv: resume_id, raw_experience_lines (cap at 300 characters), extracted_title, extracted_company, start_date, end_date. No classification column and no heuristic column.
- [ ] Write data/parser_holdout_30_fresh.meta.txt with the git commit hash of the parser, the row count, the resume IDs and the sha256 of the CSV. Do not regenerate or edit the CSV after this step.
- [ ] Copy this one CSV to ~/recruit_lens_review/parser_holdout_30_fresh.csv (create the folder if needed). I explicitly authorize this one copy outside the repo and nothing else. Print its absolute path, row count and sha256.
- [ ] The CSV contains resume text. Confirm with `git check-ignore -v` that it is ignored, and never commit or push it.

## RULES (add to .agents/AGENTS.md)
- [ ] A metric must measure the thing it names. A number computed from the reviewer's labels, or graded by your own keyword lists, is not a measurement of the parser. Label self-graded numbers "self-graded" and never put them in a pass/fail table.
- [ ] Every figure in a report comes from a saved file with file:key, and make_report.py exits non-zero on any missing key.
- [ ] Test counts come from saved pytest output (junit xml), never from coverage.json.
- [ ] No feature or test without a requirement in docs/SPEC.md. Do not add webhooks or roles the SPEC does not have.

## GATE A: REPORT INTEGRITY (stop if not met)
- [ ] A.1: Replace dev_set_holdout_30 clean/fragment with real measurement against reviewer labels
- [ ] A.2: Remove 40-resume audit "96.48% clean" from pass/fail tables; report row-count change as fact
- [ ] A.3: Explain MiniLM RSS 363.3 MB vs earlier measurements; fix or restate cap
- [ ] A.4: Test counts from saved pytest output; map "7 owed security tests" to SPEC requirements; remove tests with no requirement

## GATE B: PERFORMANCE (stop if not met)
- [ ] Explain 225.91s/375.2MB vs 342.55s/447.4MB difference
- [ ] Run 200-resume benchmark 3 times (median, per-stage, peak RSS)
- [ ] Bars: ≤300s wall time and ≤400MB RSS
- [ ] Use process pool for PDF parsing (2 workers), per-file timeouts, cache parse results, embed in streamed batches, release page objects
- [ ] If RAM bar cannot be met, report cause and peak with model loaded vs unloaded

## GATE C: ROUTER TESTS
- [ ] Every router module at ≥70% coverage
- [ ] Named tests for: isolation, state transitions, email send gates, CSV injection, hard delete, data export, what-if, SSE progress/cancel, upload limits, login throttling, refresh reuse
- [ ] Save per-module coverage

## GATE D: RETRIEVAL
- [ ] D.1: List dropped gold pairs; add confidence intervals at N=31
- [ ] D.2: Print full corpus-wide and within-resume table
- [ ] D.3: Regression analysis vs old project; old vs new chunker control experiment
- [ ] D.4: Count mojibake chunks; apply ftfy+placeholder cleaning before chunking
- [ ] D.5: Vocabulary-mismatch table with BM25 vs dense/hybrid comparison

## GATE E: SCORING VALIDITY
- [ ] Re-run weak labels, training, tiers on cleaned parser + expanded taxonomy
- [ ] Print from saved files: Spearman, tier thresholds, per-role-family, per-category taxonomy coverage, years_gap and title_match before/after parser change

## GATE F: CRITIC AND INJECTION
- [ ] F.1: Report upper bound for 0/60 false accepts or extend to 150 sentences
- [ ] F.2: Per-variant injection recording (10 variants including non-English and split-across-chunks)
- [ ] F.3: Do not change critic threshold until reviewer labels come back

## GATE G: MODEL COMPARISON AND LATENCY
- [ ] Compare qwen, gpt-oss-20b, gpt-oss-120b on same 20 candidates with real prompts
- [ ] Critic-checked pass rate, latency, tokens, TPM/RPM limits

## GATE H: BATCH 4 EVIDENCE
- [ ] Postgres test and Alembic migration against Supabase
- [ ] OpenAPI route list, response headers, rate limits, /ready, /metrics
- [ ] CI run IDs for branch, main, tags v0.5.1–v0.5.3
