# OPEN ITEMS — FIX ROUND 3 & BATCH 5

Saved from user request on 2026-10-29.

## A. INTEGRITY (STOP CONDITION)
- [x] A.1: Run `git log -p` for every `docs/eval_*.json`, list each change not produced by a script, regenerate each from its script. Delete any non-reproducible value and report as "not measured".
- [x] A.2: Every eval file must carry `generated_by` (script name), `git_commit`, and `input_sha256` written by the script itself. `make_report.py` refuses files without them. Add CI check failing if a `docs/eval_*.json` changes in a commit that does not also change or call its script.
- [x] A.3: Coverage explanation: 2338/4241 is 55.1%, not 82%. Print covered and total statements straight from `docs/coverage.json` and explain the earlier 3415/4246.
- [x] A.4: Critic Wilson interval: compute intervals with a function, and either run the 150-sentence set and save it, or delete the N=150 claim.
- [x] A.5: Injection: save per variant (10 variants) whether the model obeyed and whether the critic caught it. Revert guardrail regex so it does not match bare "ignore", "override" or "forget". Run sanitizer over 200 real resume chunks and report altered count (target 0 unless injection present).
- [x] A.6: Fresh holdout sha256 & row count: check reviewer sha256 `3c06c179259f8c7c4425615cb0836c73ccedc3e016686de519e3a4ee8e39500b` and row count (171 rows) vs recorded in `data/parser_holdout_30_fresh.meta.txt`.
- [x] A.7: 200-resume benchmark: report run 1 with cold parse cache separately from runs 2 and 3, report peak RSS summed over parent and all worker processes. Bars: ≤300s, ≤400MB.
- [x] A.8: Retrieval wording: remove claim that dense or MiniLM outperforms BM25 at N=31 with overlapping CIs. Explain drop from 64.7% to 45.2% or state unexplained; state primary retrieval method and why.

## B. PARSER (STOP CONDITION)
(The reviewer labelled `data/parser_holdout_30_fresh.csv`; it is now DEV set 2. Create a new fresh holdout of 30 resumes in `data/`, gitignored, copy only that CSV to `~/recruit_lens_review/`.)
Reviewer totals on DEV set 2: 171 rows: O 127, C 2, W 6, F 14, D 17, ? 5. Real entries 135.
- [x] B.1: Duplicates: deduplicate by normalized title + dates + raw text within resume; drop undated entry matching dated entry. Target: 0 duplicates.
- [x] B.2: Fragments (14): use features (leading action verb, ending in preposition/article/conjunction/open paren, >8 words, skill-list/cert lines, award lines). Target: <5% fragments.
- [x] B.3: Wrong titles (6): fix character dropping ("Front-End", "4/5"), one-word titles ("Specialist", "Assistant"), title fused with description. Split title from description. Target: <8% wrong/missing.
- [x] B.4: Remove leftover "Company Name City" in title. Set date to null and confidence low when end is before start.
- [x] B.5: Company unreliable: set company to null unless passes organization check, never store salary text, do not use company in any feature.
- [x] B.6: Expose `date_known` per entry; years of experience must fall back to stated "N years" or marked missing, never 0.
- [x] New fresh holdout: sample 30 new resumes not in first-100, audit-40, dev-30 (parser_holdout_30.csv), or dev2-30 (parser_holdout_30_fresh.csv). Save to `data/parser_holdout_30_fresh_v2.csv` (gitignored), write meta.txt, copy to `~/recruit_lens_review/parser_holdout_30_fresh_v2.csv`.

## C. STILL OWED BEFORE BATCH 6 (Keep in OPEN_ITEMS.md)
- [ ] Scoring validity: Spearman of must_have_coverage alone vs label and model gain over it, tier thresholds chosen on training folds with Wilson intervals on held-out folds, per-role-family metrics.
- [ ] Model comparison with real Explainer, Interviewer and Email prompts on 20 candidates for qwen, gpt-oss-20b and gpt-oss-120b.
- [ ] Alembic migration and full test suite on Supabase Postgres (never print URL).
- [ ] Response headers, rate limits, /ready and /metrics from running app.
- [ ] CI run IDs for v0.5.1, v0.5.2, v0.5.3.
- [ ] Confirm webhook test and code are removed.

## BATCH 5 TASKS
- [ ] Frontend: Login only (no signup), demo credentials in env/README.
- [ ] Do not display company. Show title and dates; show "dates missing" instead of 0 for years.
- [ ] "template" badge and "generating" state for LLM text. Email editor shows "Dry run" or "Live" indicator.
- [ ] "insufficient information" state for abstained candidates.
- [ ] Migrate shell to Tailwind + shadcn/ui, remove custom CSS.
- [ ] Use generated OpenAPI types only. Playwright runs against seeded backend with synthetic data (no real resumes, no resume text committed).
- [ ] Implement all 17 screens per docs/SPEC.md:
  1. Ranked table: server-side sort/filter/page, tier badges, missing must-haves, bulk select, quick actions.
  2. Candidate detail: score gauge, plain reasons, matched/inferred/missing skills, evidence highlighting, timeline, what-if, questions, copilot.
  3. Compare view: 2-3 candidates side by side.
  4. Decision dialog with required note & audit history.
  5. Email editor: draft vs edited, Dry run / Live indicator, confirmation step.
  6. Interview scorecard form and post-interview decision.
  7. Pipeline board with dnd-kit calling validated state machine.
  8. Reports: funnel, agreement, Recharts.
  9. Blind-mode toggle.
- [ ] Tests: Vitest for components/hooks, Playwright end-to-end journey.
- [ ] Capture 5-6 synthetic screenshots into docs/ for README.
- [ ] Update PROJECT_EXPLAINED.md, README, tag v0.6.0.
