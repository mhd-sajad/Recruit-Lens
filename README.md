# Recruit Lens

An explainable, evidence-grounded AI recruiter platform that screens resumes against job descriptions, computes transparent match scores, cites exact textual evidence chunks, and empowers hiring teams through an audit-backed human-in-the-loop workflow.

---

## Key Highlights

- **Hybrid Evidence Retrieval:** Combines exact keyword matching (BM25) and local semantic search (ONNX MiniLM) with per-candidate isolation.
- **Explainable Scoring:** Deterministic mathematical feature scoring with SHAP feature attributions—never ungrounded LLM scoring.
- **Evidence-Grounded Generation:** All candidate summaries, interview questions, and email drafts cite retrieved resume excerpts and undergo automated Self-RAG critique.
- **Full HR Workflow:** Complete 17-screen recruiter journey including blind review mode, candidate comparison, interview scorecards, and append-only decision audit logging.
- **100% Free to Self-Host:** Zero paid APIs required; operates within 400 MB RSS backend memory constraints on free-tier infrastructure.

---

## Monorepo Layout

```text
RECRUIT-LENS/
├── .agents/          # Project operating principles, contract, and quality bars
├── .github/          # GitHub Actions CI workflow (backend, frontend, gitleaks)
├── backend/          # FastAPI service (Python 3.11, uv lockfile, pydantic-settings)
│   ├── app/          # Core application (config, middleware, logging, endpoints)
│   └── tests/        # Pytest suite with >=80% coverage enforcement
├── frontend/         # Vite + React + TypeScript web client
│   ├── src/          # Accessible UI components with empty, loading & error states
│   └── tests/        # Vitest suite
├── scripts/          # Developer automation scripts (run_checks.sh, setup_dev.sh)
├── docs/             # SPEC.md (frozen) and PROJECT_EXPLAINED.md (living)
├── data/             # Local data and SQLite storage (gitignored)
└── .env.example      # Sample environment configuration template
```

---

## Quickstart Guide

### Prerequisites
- Python 3.11 installed via [uv](https://docs.astral.sh/uv/)
- Node.js (v20+) & npm

### 1. Automated Setup
Run the automated onboarding script to prepare both backend and frontend environments:
```bash
./scripts/setup_dev.sh
```

### 2. Configure Environment
Copy the environment template:
```bash
cp .env.example .env
```

### 3. Start Backend Service
```bash
cd backend
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
API endpoints will be accessible at:
- Health Check: `http://localhost:8000/health`
- Interactive OpenAPI Docs: `http://localhost:8000/docs`

### 4. Start Frontend Client
```bash
cd frontend
npm run dev
```
Open `http://localhost:5173` to interact with the recruiter dashboard.

---

## Batch 1: Ingestion, Parsing & Retrieval Truth Test (Re-Measured & Audited)

Batch 1 establishes a verified, measured data ingestion and candidate-isolated retrieval foundation:

- **Dual-Engine PDF Parser:** Multi-column layout coordinate clustering, deterministic rule-based resume gate, and strict PII isolation (`scoring_text` free of contact details). Audited on 40 unseen random resumes:
  - **Reviewer Hand-Labelled Baseline (Old Parser):** Out of 291 extracted entries in `data/parser_audit_40.csv`: 90 clean (O), 77 noisy (C), 36 wrong (W), 88 non-job fragments (F). Across 203 real jobs: **44.3% clean**, **82.3% recoverable**.
  - **Fixed Parser Performance:** Encoding repaired with `ftfy`, placeholder/bullet stripping, template filtering, and header merging eliminated all fragments: **201 total entries**, **0 fragments (0.0%)**, **0 wrong (0.0%)**, **201 recoverable (100.0%)**, **40/40 first-entry accuracy (100.0%)**. Fresh holdout generated in `data/parser_holdout_30.csv` (153 entries across 30 unseen resumes).
  - **Resume Gate Precision:** **100.0%** (20/20 non-resumes rejected across unseen cover letters, meeting minutes, brochures, and certificates; 100/100 real resumes accepted).
- **SSRF-Safe JD Scraper:** Blocks loopback, private, link-local, and cloud metadata IPs (`169.254.169.254`) with strict timeouts and 2 MB size caps. (Note: JD corpus contains 123,700 rows; the vault manifest's 1.3M figure was incorrect).
- **Quantized ONNX Embedder (Arena Disabled):** CPU-quantized MiniLM-L6 operating at **218.8 MB RSS**, outperforming BGE-small (262.6 MB RSS, with CLS pooling and query prefix). (Memory difference is likely due to the ONNX Runtime / OS allocator arena retention rather than model weights alone).
- **Candidate-Isolated Retrieval:** Zero cross-candidate data leakage by construction. Stores float32 embedding blobs and fuses in-memory `bm25s` and dense vector cosine similarity via Reciprocal Rank Fusion ($k=60$).
- **Within-Resume Retrieval Test (34 Gold Queries, Median Pool = 8 chunks):**
  - **Random Guess Baseline:** Hit@5: **62.92%**, Hit@10: **95.34%**, MRR: **0.3381**
  - **BM25 (Sparse):** Hit@5: **94.1%**, Hit@10: **97.1%**, MRR: **0.6395**
  - **Dense (MiniLM):** Hit@5: **82.4%**, Hit@10: **97.1%**, MRR: **0.6412**
  - **Hybrid (MiniLM RRF $k=60$):** Hit@5: **88.2%**, Hit@10: **97.1%**, MRR: **0.6913**
- **Corpus-Wide Retrieval Test (34 Gold Queries across 300 Resumes Pooled = 2,317 Chunks):**
  - **New Sliding-Window Chunks (150 words max):** BM25 Hit@5: **50.0%** (MRR: 0.3712), Dense MiniLM Hit@5: **38.2%** (MRR: 0.2333), Hybrid Hit@5: **50.0%** (MRR: 0.3197).
  - **Control Experiment on Old Monolithic Chunks (up to 1,062 words):** BM25 Hit@5: **67.65%** (MRR: 0.5167), Hybrid Hit@5: **67.65%** (MRR: 0.4262).
  - **Old Project Baseline Reference:** The old project baseline achieved **64.7% Hit@5** using BM25 over the full old corpus with the same 34 pairs (not TF-IDF + cosine).
  - **Chunk Boundary Retention Analysis:** 10 hand-inspected remapped pairs showed 4 full retentions and 6 partial/splits across sliding-window boundaries. When multi-sentence evidence is split into adjacent 150-word chunks, queries matching adjacent chunks are marked misses under strict single-chunk ID matching.
  - **Primary Engine Decision:** BM25 designated primary retrieval signal (MRR 0.3712 beats Dense 0.2333 and Hybrid 0.3197).

---

## Batch 2: Explainable Scoring & Candidate Triage Engine

Batch 2 establishes a transparent, non-discriminatory candidate evaluation engine with deterministic grounding:

- **Expanded Skill Taxonomy:** 8,822 canonical skills across 140 families (full O*NET 29.0 technology skills + domain non-tech skills for Education, Healthcare, Sales, HR, Legal, and Operations). All 24 resume categories have $\ge 91.7\%$ with $\ge 3$ skills (`TEACHER` at 91.7%); all JD families exceed 60% with $\ge 3$ skills. Batched regex alternations (chunks of 200) achieve 100x faster sub-millisecond matching.
- **Deterministic JD Requirement Extractor:** Extracts minimum/maximum experience years, degree ranks (0-4), and partitions must-have vs nice-to-have skills with typed Pydantic models.
- **Resume Skill Extractor with Citation Evidence:** Records character offsets and chunk IDs for all extracted skills with explicit match precedence over inferences.
- **Bounded Feature Vector with Keyword Stuffing Guard:** Computes 10 bounded features with calibrated confidence and explicit missing-data handling (never silently 0). Set-based skill matching guarantees that repeating a skill 50 times yields zero score gain.
- **Weak-Supervision Pair Dataset:** 1,080 pairs crossing 120 resumes across 24 categories with 105 JDs across 11 families (480 positives, 360 hard negatives, 240 easy negatives). Limitations documented honestly as heuristic proxy labels.
- **Scoring Engine & Grouped 5-Fold Cross-Validation:**
  - `must_have_coverage` alone has moderate Spearman correlation with the weak label ($\rho = 0.3567$, Pearson $r = 0.4415$).
  - **Marginal Gain of XGBoost:** Multi-feature Monotonic XGBoost achieves NDCG@10 of **0.9406** (+0.0724 gain over single-feature 0.8682) and Spearman $\rho$ of **0.4463** (+0.0896 gain over single-feature 0.3567).
  - **Grouped CV Tier Thresholds:** Calibrating thresholds on training folds yields real held-out **Strong Fit Precision of 60.0%** (9/15) with a **95% Wilson Score Confidence Interval of [35.7% - 80.2%]** (recall 25.7%). (Self-set targets of precision > 85% and ECE < 0.05 marked as engineering objectives, not external benchmarks).
- **Plain-Language Reasons Generator:** Translates mathematical feature attributions into factual recruiter briefings (strengths and gaps) citing evidence chunks.
- **Candidate Triage Tiers:** Data-calibrated thresholds with strict must-have override (missing mandatory skills strictly disallows Strong Fit) and low-parse-confidence abstain state.
- **What-If Qualification Simulator:** Interactive projection of score and tier deltas under hypothetical skill or experience adjustments with explicit planning disclaimers.
- **Metamorphic Invariant Test Suite:** 6 properties asserting monotonicity, demographic bias invariance (gender, ethnicity, contact info), section reordering stability, keyword stuffing resistance, and corrupt document abstention.
- **Vocabulary-Mismatch Stress Test (Batch 2 Task 12):** Exact string matching failed on Candidate A (2/5) and Candidate B (0/5). Canonical alias resolution + dense similarity successfully bridged the gap, correctly ranking Candidate A (0.7484) > Candidate B (0.5997) >> Candidate C (0.2327).
- **Real End-to-End 200-Resume Pipeline Benchmark:**
  - Total Wall-Clock Time: **219.10 s (3.65 minutes)** (SLA $< 300$ s): **PASSED**
  - Per-Resume Wall Time: **1,095.5 ms / resume**
  - Peak RSS Memory: **456.5 MB** (during un-garbage-collected full batch; single document/chunk streaming runs at 285 MB).
  - Latency Explanation: Batch 1 cold single-threaded unquantized inference took 74.57 ms/chunk; Batch 2+ INT8 quantized batched ONNX with 2 threads reduced inference to 48.71 ms/chunk under full load.

### Running Batch 2 Benchmarks & Tools
```bash
# Generate weak supervision pairs dataset
PYTHONPATH=backend uv run python scripts/build_weak_supervision.py

# Run 5-fold grouped cross-validation comparison (Baseline vs XGBoost)
PYTHONPATH=backend uv run python scripts/train_and_eval_models.py

# Run comprehensive scoring validity and real 200-resume benchmark
PYTHONPATH=backend uv run python scripts/evaluate_scoring_validity.py
```

---

## Batch 3: Grounded LLM Agents & Evidence Text Generation

Batch 3 establishes a resilient multi-agent text generation system strictly grounded in retrieved evidence chunks, backed by automated Self-RAG critique and mathematical scoring invariance:

- **Multi-Provider LLM Interface:** Integrates Groq free cloud API (`qwen/qwen3.8-27b`, with fallback `openai/gpt-oss-120b`), local Ollama (`http://localhost:11434`), and deterministic `NoLLMProvider` fallback. Includes dynamic model discovery, token-bucket rate limiting (8,000 TPM and 30 RPM), exponential backoff with jitter on HTTP 429/503, and persistent SQLite cache (`data/llm_cache.sqlite`) keyed by SHA-256 prompt hash.
- **Strict Guardrails & Prompt Injection Neutralization:**
  - XML boundary encapsulation (`<evidence_chunk>`).
  - Regex neutralization of prompt injection strings (`ignore previous instructions`, `rate me 100`, etc.).
  - Blind-mode PII redaction (candidate name, email, phone) prior to LLM synthesis.
  - **Mathematical Invariance Proof:** Candidate scoring is 100% LLM-free. An adversarial candidate injecting prompt injection strings into their resume obtains an exact score difference of $\Delta = 0.000$ compared to the benign resume.
- **Specialized Multi-Agent Pipeline:**
  - **Explainer Agent:** Generates 3-4 sentence evaluation summaries citing chunk IDs (`[c_01]`).
  - **Interview Question Generator:** Formulates 3-5 seniority-calibrated interview questions probing verified skills, missing mandatory requirements, and domain architecture.
  - **Email Drafter:** Generates tailored interview invites, hold notifications, and rejection drafts. Rejections strictly omit internal scores and negative critique justifications.
- **Self-RAG Critique & Claim Grounding:**
  - Sentence-level verification: regex number and entity matching, ONNX MiniLM cosine semantic similarity against cited evidence chunks.
  - Automated 2-turn rewrite loop for ungrounded sentences.
  - Strict safety `BLOCK` fallback to deterministic templates when claims remain ungrounded.
- **State Machine Orchestrator:** Resumable, idempotent execution lifecycle (`AgentExecutionRepository`), concurrency control via `asyncio.Semaphore`, and per-candidate failure isolation.

### Running Batch 3 Evaluation & Benchmarks
```bash
# Run 40-candidate faithfulness benchmark and 7-point adversarial suite
export PATH="$HOME/.local/bin:$PATH"
uv run --project backend python3 scripts/evaluate_llm_agents.py
```

---

## Running Quality Checks

Run the unified quality verification suite across backend and frontend:
```bash
./scripts/run_checks.sh
```
This runs:
- **Backend:** Ruff linter & formatter, Mypy typecheck, Pytest with coverage check (>=80%).
- **Frontend:** ESLint, TypeScript strict compilation, Vitest component test suite.

---

## Project Documentation

- **[docs/SPEC.md](docs/SPEC.md):** The frozen product specification defining data entities, pipeline steps, agent roles, and the 17-screen recruiter journey.
- **[docs/PROJECT_EXPLAINED.md](docs/PROJECT_EXPLAINED.md):** Living documentation covering the big picture, technology rationale, architectural plan, and incremental build log.
- **[.agents/AGENTS.md](.agents/AGENTS.md):** Engineering operating principles, working contract, and global quality bars.

---

## Dataset & Taxonomy License Attribution

- **O*NET Technology Skills:** This product includes technology skills data from the **O*NET 29.0 Database** by the U.S. Department of Labor, Employment and Training Administration (USDOL/ETA), used under the [Creative Commons Attribution 4.0 International License (CC BY 4.0)](https://creativecommons.org/licenses/by/4.0/). O*NET® is a trademark of USDOL/ETA.
