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
  - **Structured Title Accuracy Estimate:** **87.3%** correct (across 291 audited job entries, documented in `data/parser_audit_40.csv`)
  - **Resume Gate Precision:** **95.0%** (19/20 non-resumes rejected across unseen cover letters, meeting minutes, brochures, and certificates)
- **SSRF-Safe JD Scraper:** Blocks loopback, private, link-local, and cloud metadata IPs (`169.254.169.254`) with strict timeouts and 2 MB size caps.
- **Quantized ONNX Embedder (Arena Disabled):** CPU-quantized MiniLM-L6 operating at **164.2 MB RSS** at **5.05 ms/chunk**, outperforming BGE-small (178.7 MB RSS at 8.39 ms/chunk).
- **Candidate-Isolated Retrieval:** Zero cross-candidate data leakage by construction. Stores float32 embedding blobs and fuses in-memory `bm25s` and dense vector cosine similarity via Reciprocal Rank Fusion ($k=60$).
- **Within-Resume Retrieval Test (34 Gold Queries, Median Pool = 8 chunks):**
  - **Random Guess Baseline:** Hit@5: **62.92%**, Hit@10: **95.34%**, MRR: **0.3381**
  - **BM25 (Sparse):** Hit@5: **94.1%**, Hit@10: **97.1%**, MRR: **0.6395**
  - **Dense (MiniLM):** Hit@5: **82.4%**, Hit@10: **97.1%**, MRR: **0.6412**
  - **Hybrid (MiniLM RRF $k=60$):** Hit@5: **88.2%**, Hit@10: **97.1%**, MRR: **0.6913**
- **Corpus-Wide Retrieval Test (34 Gold Queries across All 300 Resumes Pooled = 2,318 Chunks):**
  - **BM25:** Hit@1: **23.5%**, Hit@3: **47.1%**, Hit@5: **47.1%**, Hit@10: **70.6%**, MRR: **0.3702**
  - **Dense (MiniLM):** Hit@1: 14.7%, Hit@3: 38.2%, Hit@5: 38.2%, Hit@10: 44.1%, MRR: 0.2574
  - **Hybrid (MiniLM RRF):** Hit@1: 20.6%, Hit@3: 38.2%, Hit@5: 47.1%, Hit@10: 61.8%, MRR: 0.3283
  - **Primary Engine Decision:** BM25 designated primary retrieval signal (MRR 0.3702 beats Dense 0.2574 and Hybrid 0.3283).

---

## Batch 2: Explainable Scoring & Candidate Triage Engine

Batch 2 establishes a transparent, non-discriminatory candidate evaluation engine with deterministic grounding:

- **Curated Skill Taxonomy:** Backed by official O*NET 29.0 technology skills (2,500 prioritized technical skills, 2,545 aliases, 134 families) with hierarchical inference relations (e.g., Django implies Python at 0.95 confidence).
- **Deterministic JD Requirement Extractor:** Extracts minimum/maximum experience years, degree ranks (0-4), and partitions must-have vs nice-to-have skills with typed Pydantic models.
- **Resume Skill Extractor with Citation Evidence:** Records character offsets and chunk IDs for all extracted skills with explicit match precedence over inferences.
- **Bounded Feature Vector with Keyword Stuffing Guard:** Computes 10 bounded features with calibrated confidence and explicit missing-data handling (never silently 0). Set-based skill matching guarantees that repeating a skill 50 times yields zero score gain.
- **Weak-Supervision Pair Dataset:** 1,080 pairs crossing 120 resumes across 24 categories with 105 JDs across 11 families (480 positives, 360 hard negatives, 240 easy negatives). Limitations documented honestly as heuristic proxy labels.
- **Scoring Engine & Grouped 5-Fold Cross-Validation:**
  - Evaluated on 1,080 pairs grouped by `resume_id` to prevent data leakage.
  - **Weighted Baseline:** NDCG@10: **0.9255**, Spearman $\rho$: **0.3575**, MAE: **0.1736**, ECE: **0.1196**.
  - **Monotonic XGBoost:** NDCG@10: **0.9406**, Spearman $\rho$: **0.4463** (+0.0888 gain), MAE: **0.1484**, ECE: **0.0191** ($6\times$ better calibration).
  - **Winning Model:** Monotonic XGBoost shipped as primary scoring model (`backend/app/data/scoring_xgb.json` at 106 KB), with Weighted Baseline retained for zero-dependency fallback.
- **Plain-Language Reasons Generator:** Translates mathematical feature attributions into factual recruiter briefings (strengths and gaps) citing evidence chunks.
- **Candidate Triage Tiers:** Data-calibrated thresholds (Strong Fit $\ge 0.72$, Interview $\ge 0.50$, Hold $\ge 0.30$, Reject $< 0.30$) with strict must-have override (missing mandatory skills strictly disallows Strong Fit) and low-parse-confidence abstain state.
- **What-If Qualification Simulator:** Interactive projection of score and tier deltas under hypothetical skill or experience adjustments with explicit planning disclaimers.
- **Metamorphic Invariant Test Suite:** 6 properties asserting monotonicity, demographic bias invariance (gender, ethnicity, contact info), section reordering stability, keyword stuffing resistance, and corrupt document abstention.
- **Unified Evaluation Pipeline (`scripts/run_eval.py`):** Outputs `docs/eval_metrics_batch2.json` with latency and memory SLA verification:
  - Latency SLA: **10.98 ms / candidate** (Target $< 500$ ms): **PASSED**
  - Peak RSS Memory: **164.2 MB** (Target $< 400$ MB): **PASSED**
  - 200-Resume Batch Runtime: **2.20 s** (Target $< 300$ s): **PASSED**

### Running Batch 2 Benchmarks & Tools
```bash
# Generate weak supervision pairs dataset
PYTHONPATH=backend uv run python scripts/build_weak_supervision.py

# Run 5-fold grouped cross-validation comparison (Baseline vs XGBoost)
PYTHONPATH=backend uv run python scripts/train_and_eval_models.py

# Run unified system evaluation (retrieval, scoring, tiers, SLAs)
PYTHONPATH=backend uv run python scripts/run_eval.py
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
