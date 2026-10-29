# FINISH PLAN — RECRUIT LENS COMPLETE IMPLEMENTATION

## PHASE 0: CLOSE-OUT (fix, then tag v0.6.0)
- [x] 0.0 Check CI result for branch `fix/batch-4-integrity-and-parser` (commit `84c6770`). CI Run ID 40844764118 passed.
- [x] 0.1 Router coverage contradiction resolved: root `.coveragerc` captures ASGI event loops with `concurrency = greenlet, thread`. Router modules 94.03% to 100.00% (overall 89.21% across 3,853 statements) in `docs/eval_router_modules_coverage.json`.
- [x] 0.2 Parser metric: per-entry alignment against reviewer labels on dev set 2 (data/parser_holdout_30_fresh.csv, 171 rows) saved in `docs/eval_parser_dev2_alignment_report.json` (126/135 matched, 93.33%, 0 fragments, 0 duplicates, 130 recoverable 96.30%).
- [x] 0.3 Embedder footprint: measured in isolated subprocesses with `MALLOC_ARENA_MAX=2` reading `/proc/self/status` VmRSS across baseline, imports, load, and inference. Saved in `docs/eval_embedder_footprint_report.json`.
- [x] 0.4 200-resume benchmark: measured cold (289.16s, 317.4MB RSS) and warm median (143.81s, 313.8MB RSS) across process tree. Hand-written narrative removed and replaced with measured speedup factor in `docs/eval_benchmark_200.json`.
- [x] 0.5 Scoring validity: 12-feature XGBoost Grouped CV (Spearman rho 0.4463, gain +0.0897, NDCG@10 0.9406, gain +0.0725, Strong Fit Precision 60.0% [Wilson CI: 35.75% - 80.18%]) and 11 role-family breakdowns in `docs/eval_scoring_validity_report.json`.
- [x] 0.6 Injection: 10 live adversarial variants tested against Groq LLM with raw outputs recorded in `docs/eval_injection_live.json` (100.0% neutralized). Sanitizer altered 0 of 200 real chunks.
- [x] 0.7 Retrieval wording: within-resume vs corpus-wide (2,275 pooled chunks) drop cause reported, primary keyword engine stated without claiming winner in `docs/eval_corpus_retrieval_report.json`.
- [x] 0.8 Owed items: PostgreSQL 18.6 connectivity & Alembic migrations verified at head; running app `/ready`, `/metrics`, and response headers tested; model comparison in `docs/eval_model_comparison_report.json`.
- [ ] 0.9 Phase 0 Self-audit, green CI, merge, tag v0.6.0.

## PHASE 1: RECRUITER PORTAL (tag v0.7.0)
- [ ] 1.1 Migrate frontend shell to Tailwind CSS + shadcn/ui, delete custom CSS.
- [ ] 1.2 Generate TypeScript types from backend OpenAPI schema (no hand-written api.ts).
- [ ] 1.3 Add any missing backend endpoints needed by screens (reports: funnel counts, system-vs-recruiter agreement; settings; blind-mode flag) with tests.
- [ ] 1.4 Build all 17 screens in docs/SPEC.md against real API:
  - Login only (no signup), demo credentials banner from env/README.
  - Candidate display: title + dates, "dates missing" instead of 0, no company displayed.
  - LLM text: deterministic template text immediately with "template" badge & "generating" state. Email editor shows draft vs edited, "Dry run" / "Live" indicator, confirmation step. Abstained candidates show "insufficient information".
  - 17 screens: Ranked table, Candidate detail, Compare view (2-3), Decision dialog, Email editor, Interview scorecard & post-interview decision, Pipeline board with dnd-kit, Reports (Recharts), CSV & PDF export, Settings & blind-mode toggle, etc.
- [ ] 1.5 Vitest tests for components and hooks.
- [ ] 1.6 Playwright end-to-end journey against seeded backend (synthetic data only, no real resumes committed).
- [ ] 1.7 Capture 5-6 synthetic screenshots for docs/ and README.
- [ ] 1.8 Phase 1 Self-audit, green CI, merge, tag v0.7.0.

## PHASE 2: EXTRAS AND HARDENING (tag v0.8.0)
- [ ] 2.1 Copilot: grounded Q&A over one candidate's evidence (or job's candidates) using hybrid retrieval; citations required; answers "not found in this resume" when evidence missing; critic applied; on-demand only.
- [ ] 2.2 Blind mode end to end: backend flag, UI toggle, PII redaction before LLM call. Tests prove identity never appears. Document limitations.
- [ ] 2.3 MCP server (official Python SDK): read-only tools (search_candidates, get_candidate_report, list_jobs), draft_email. Decision tool requires one-time confirmation token from web UI. Scoped API key.
- [ ] 2.4 Evaluation and monitoring: store eval runs in DB, dashboard metrics (retrieval, tier PR, agreement, faithfulness), feature drift with PSI/KS. Retraining script with model version registry.
- [ ] 2.5 Security pass: pip-audit, npm audit, OWASP checklist fixes (authz, injection, SSRF, upload, CSV injection, rate limits, secrets, no PII logs), list accepted risks.
- [ ] 2.6 Resilience tests: LLM down, quota exhausted, DB lock, worker killed mid-batch, corrupt PDF, 100-page PDF, duplicate uploads.
- [ ] 2.7 Performance pass against bars (300s, 400MB for 200 resumes) with real timings.
- [ ] 2.8 Phase 2 Self-audit, green CI, merge, tag v0.8.0.

## PHASE 3: DEPLOY, DOCUMENT, RELEASE (tag v1.0.0)
- [ ] 3.1 Verify free-tier limits (Hugging Face Spaces, Render, Vercel, Cloudflare Pages, Supabase). Choose backend host, record limits/sleep/cold-start in PROJECT_EXPLAINED.md.
- [ ] 3.2 Multi-stage Dockerfile with ONNX model baked in, start migrations, health check, non-root user. Frontend deploy config. CORS locked, HTTPS only, rate limits tuned.
- [ ] 3.3 Demo workspace with synthetic data only and demo login in README. Groq notice.
- [ ] 3.4 Final verification: fresh-clone quickstart, CI green, gitleaks across full history, Playwright against deployed/local URLs, DEPLOY_STEPS.md if account action needed, make_report.py final run.
- [ ] 3.5 README: mermaid diagram, screenshots, quickstart, make_report table, Limitations section, MIT licence, O*NET CC BY 4.0 attribution.
- [ ] 3.6 Finalize PROJECT_EXPLAINED.md (5-minute demo, how to explain).
- [ ] 3.7 Generate docs/FINAL_REPORT.md via script.
- [ ] 3.8 Tag v1.0.0 after green CI on main.
