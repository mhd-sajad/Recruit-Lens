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
