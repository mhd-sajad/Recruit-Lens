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

## Batch 1: Ingestion, Parsing & Retrieval Truth Test

Batch 1 establishes a verified, measured data ingestion and candidate-isolated retrieval foundation:

- **Dual-Engine PDF Parser:** Multi-column layout coordinate clustering, deterministic rule-based resume gate, and strict PII isolation (`scoring_text` free of contact details). Measured on 100 real resumes and 20 non-resumes:
  - **Structured Title Extraction Rate:** **98.0%** (jumping from old 33.3% baseline)
  - **Resume Gate Precision:** **100.0%** (20/20 non-resumes rejected)
  - **Resume Gate Recall:** **100.0%** (100/100 real resumes accepted)
  - **Parse Failures:** **0.0%** (0/100)
- **SSRF-Safe JD Scraper:** Blocks loopback, private, link-local, and cloud metadata IPs (`169.254.169.254`) with strict timeouts and 2 MB size caps.
- **Quantized ONNX Embedder:** CPU-quantized MiniLM-L6 operating at **132.3 MB RSS** (well below the 350 MB ceiling) at **74.6 ms/chunk**, outperforming BGE-small (which breached RAM at 750.5 MB).
- **Candidate-Isolated Retrieval:** Zero cross-candidate data leakage by construction. Stores float32 embedding blobs and fuses in-memory `bm25s` and dense vector cosine similarity via Reciprocal Rank Fusion ($k=60$).
- **Truth Test on 34 Gold Pairs:**
  - **BM25 (Sparse):** Hit@5: **100.0%** (95% CI: [100.0%, 100.0%]), MRR: **0.8456** (95% CI: [0.7573, 0.9289])
  - **Hybrid (RRF $k=60$):** Hit@5: **97.1%** (95% CI: [91.2%, 100.0%]), MRR: **0.7966** (95% CI: [0.6936, 0.8971])
  - **Primary Engine Decision:** BM25 designated primary retrieval signal, with dense semantic search as secondary verification.

### Running Batch 1 Benchmarks & Tools
```bash
# Run parser benchmark on 100 real resumes and 20 non-resumes
bash scripts/measure_parser.sh

# Run embeddings benchmark and 34-pair truth test
cd backend && uv run python ../scripts/benchmark_retrieval_and_truth_test.py

# Launch interactive CLI to label new query-chunk ground truth pairs
cd backend && uv run python ../scripts/label_pairs.py
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
