# Recruit Lens — Project Explained

## Section 1: The Big Picture

### What Recruit Lens Is
Recruit Lens is an explainable, evidence-grounded candidate evaluation and recruiter platform. It assists hiring teams by ingesting a job description (JD) and a batch of resumes, extracting requirements and candidate qualifications, performing isolated hybrid retrieval of evidence, computing mathematically transparent fit scores, and producing plain-language rationale, tailored interview questions, and email drafts—all strictly grounded in cited resume excerpts.

### Objective & Who It Helps
- **Objective:** Give recruiters a reliable, fair, and fast screening copilot that eliminates manual resume skimming fatigue while preventing black-box automation errors.
- **Who It Helps:** Recruiters, hiring managers, and HR specialists who need to screen tens or hundreds of candidates with high consistency, verifiable reasoning, and zero per-resume subscription costs.

### Why It Differs from ATS Keyword Filters and Cloud Black-Box Screeners
1. **Vs. Traditional ATS Keyword Filters:**
   - Standard ATS filters perform rigid string matching. They fail when candidates use synonyms (e.g., "NodeJS" vs. "Node.js", "ML" vs. "Machine Learning") or describe accomplishments conceptually.
   - Recruit Lens utilizes hybrid keyword (BM25) and semantic retrieval backed by a standardized skills taxonomy (ESCO), capturing both exact specialized terminology and conceptual equivalents.
2. **Vs. Cloud Black-Box AI Screeners:**
   - Commercial AI screeners send sensitive personal resumes to proprietary cloud APIs, returning opaque numbers with unverified summaries and hallucinated claims.
   - Recruit Lens separates scoring from text generation: scoring is calculated through deterministic features and explainable models (never an ungrounded LLM score). Every generated explanation, interview question, and draft must explicitly cite retrieved evidence chunks and pass an automated critique check.
3. **Full HR Workflow:**
   - Rather than just producing a score spreadsheet, Recruit Lens supports the end-to-end recruiter decision journey (shortlist, interview, hold, reject, hire, scorecard recording, audit logs) while ensuring no email or decision is ever dispatched without an explicit human click.
4. **Free to Self-Host:**
   - Built to run efficiently within free-tier resource boundaries (under 400 MB RSS for the backend engine) without mandatory credit-card dependencies or paid SaaS subscriptions.

---

## Section 2: The Toolbox

### FastAPI (Backend Framework)
- **What it is:** A modern, high-performance web framework for building Python APIs based on standard type hints.
- **Why chosen:** High throughput, native async support, automatic OpenAPI documentation, and minimal memory overhead.
- **How it helps here:** Serves as the robust engine routing parsing, retrieval, scoring, and orchestrator tasks with structured logging and standardized error handling.
- **Alternatives considered:** Django (rejected: too heavyweight, excessive ORM overhead for lightweight ephemeral containers); Flask (rejected: lacks native async and modern type-driven schema validation).

### Pydantic & Pydantic-Settings (Configuration & Validation)
- **What it is:** Data validation and settings management library using Python type annotations.
- **Why chosen:** Enforces strict environment variable typing, validates configuration on startup, and fails fast on invalid configs.
- **How it helps here:** Completely eliminates hardcoded paths and config bugs across development, CI, and local deployment.
- **Alternatives considered:** Raw `os.environ` or `python-decouple` (rejected: lacks automatic type coercion, regex validation, and structured error diagnostics).

### Vite + React + TypeScript (Frontend)
- **What it is:** Fast next-generation frontend tooling pairing React with strict TypeScript compilation.
- **Why chosen:** Sub-second HMR, lightweight production bundles, strict type safety, and rich component ecosystem.
- **How it helps here:** Delivers the 17-screen interactive recruiter journey with keyboard accessibility, responsive state management, and clear loading/empty/error states.
- **Styling Architecture & Correction:** While Batch 0 initialized a basic vanilla CSS shell, this was an unmeasured baseline. Batch 5 will migrate the shell to **Tailwind CSS + shadcn/ui** because the full 17-screen recruiter workflow requires highly accessible data tables (filtering, sorting, pagination), modal dialogs, candidate drag-and-drop boards, and metric charts. Custom CSS is unsuited for maintaining these complex accessible components reliably.
- **Alternatives considered:** Streamlit (rejected: difficult to build customized, keyboard-accessible multi-step recruiter workflows and audit controls); Next.js (rejected: unnecessary SSR complexity and higher hosting overhead for a client-driven dashboard).

### uv (Python Package & Environment Manager)
- **What it is:** An extremely fast Python package manager and resolver written in Rust.
- **Why chosen:** Installs dependencies in milliseconds, deterministically locks environments with `uv.lock`, and manages Python versions without system-level conflicts.
- **How it helps here:** Guarantees identical, reproducible builds across local development and GitHub Actions CI.
- **Alternatives considered:** Poetry or Pipenv (rejected: significantly slower dependency resolution and higher disk footprint); raw pip + requirements.txt (rejected: non-deterministic transitive dependency resolution without locks).

### Pytest & Vitest (Testing Frameworks)
- **What it is:** Standard test runners for Python and TypeScript ecosystems.
- **Why chosen:** Fast test execution, rich assertion syntax, built-in coverage reporting, and seamless CI integration.
- **How it helps here:** Enforces the mandatory 80%+ coverage bar on core backend logic and validates frontend UI state handling.
- **Alternatives considered:** Unittest / Jest (rejected: slower execution speed and more complex ESM setup).

### Ruff & ESLint (Linters & Formatters)
- **What it is:** Blazing-fast linters enforcing style, safety, and modern idioms in Python and TypeScript.
- **Why chosen:** Ruff executes in milliseconds; ESLint provides comprehensive TypeScript static analysis.
- **How it helps here:** Maintains clean, strictly typed code and prevents bugs before tests even run.
- **Alternatives considered:** Flake8 + Black + Isort (rejected: slower multi-tool coordination compared to unified Ruff).

### Gitleaks (Security Secret Scanner)
- **What it is:** A dedicated SAST tool for detecting hardcoded secrets, API tokens, and private keys.
- **Why chosen:** Native GitHub Actions and pre-commit support, high accuracy, and zero secret tolerance.
- **How it helps here:** Enforces the stop-the-line security rule by preventing accidental leaks of keys or credentials.
- **Alternatives considered:** TruffleHog (rejected: heavier container requirements on lightweight CI runners).

---

## Section 3: The Plan

### Phase 1: Foundation & Scaffold (Current)
- Scaffolding monorepo: `backend/`, `frontend/`, `scripts/`, `docs/`.
- Strict environment validation via `pydantic-settings`.
- Pre-commit hooks and GitHub Actions CI (lint, typecheck, test, gitleaks).
- Core documentation: `README.md`, `docs/SPEC.md`, `docs/PROJECT_EXPLAINED.md`.

### Phase 2: Resume & JD Parsing and Validation
- PDF/DOCX text extraction with parse confidence heuristics.
- Structured JD requirement extraction (must-haves, nice-to-haves, experience, education).
- Candidate isolation and chunking pipeline.

### Phase 3: Hybrid Retrieval & Skills Matching
- Local vector indexing with ONNX embeddings (`all-MiniLM-L6-v2`) and BM25 keyword index.
- Two-stage skill matcher against the canonical ESCO taxonomy.
- Per-candidate retrieval isolation.

### Phase 4: Explainable Scoring Engine
- Deterministic feature extraction (skills overlap, experience delta, education match).
- XGBoost scoring model with SHAP feature contribution breakdown.
- Tier assignment rules (disqualifying missing must-haves from Strong Fit; abstaining on low parse confidence).

### Phase 5: Evidence-Grounded Agent Generation & Self-RAG Critique
- Orchestrated agent pipeline: Explainer, Interview Questions, Email Drafts.
- Self-RAG Critique agent checking every generated claim against cited evidence chunks.
- Blind mode data scrubbing.

### Phase 6: Recruiter Workflow & 17-Screen Frontend
- Full candidate pipeline board, comparison panel, and what-if scoring analysis.
- Decision recording, audit logging, and human-in-the-loop email dispatch.
- Reporting, CSV/PDF export, and system vs. HR agreement metrics.

---

## Section 4: What We've Built So Far (Build Log)

### Component: Frozen Product Specification (`docs/SPEC.md`)
- **What it is:** The complete, authoritative reference specification defining Recruit Lens capabilities, pipeline stages, agent roles, tiers, rules, recruiter journey screens, and data entities.
- **Why:** Establishes a frozen ground-truth contract that all subsequent implementation batches cite and adhere to without requirement drift.
- **How it works:** Stored verbatim in `docs/SPEC.md` as an immutable project baseline.
- **How it helps here:** Prevents feature creep and keeps development aligned with the 17-screen journey and strict non-goals.
- **Alternatives considered:** Scattered issue descriptions or changing README notes (rejected: leads to architectural inconsistency and scope drift).

### Component: Project-Scoped Operating Principles & Working Contract (`.agents/AGENTS.md`)
- **What it is:** Operating rules, decision principles, working contract, and global quality bars governing code quality, testing, security, and verification.
- **Why:** Codifies non-negotiable constraints: 80%+ test coverage, sub-400MB memory ceiling, evidence citations for all AI outputs, and stop-the-line security response.
- **How it works:** Extends the 10 core principles with explicit contract obligations and reporting standards.
- **How it helps here:** Keeps every incremental commit disciplined, verified with measurements, and independently reviewable.
- **Alternatives considered:** Relying on informal instructions (rejected: high risk of regressions or overlooked safety bars).

### Component: Backend Service & Dependency Lock (`backend/`)
- **What it is:** Python 3.11 FastAPI package configured via `pyproject.toml` and locked deterministically using `uv.lock`.
- **Why:** Enforces modern, typed Python with sub-second dependency installation and zero drift across developer and CI environments.
- **How it works:** Managed through `uv` with strict type checking (`mypy`), linting (`ruff`), and async testing with coverage (`pytest-cov`).
- **How it helps here:** Provides the foundation for lightning-fast backend execution while keeping RAM footprints minimal.
- **Alternatives considered:** Poetry or raw requirements.txt (rejected: Poetry is significantly slower; requirements.txt lacks deterministic dependency graph resolution).

### Component: Dynamic Environment Configuration (`backend/app/config.py` & `.env.example`)
- **What it is:** Type-safe settings management using `pydantic-settings` with zero hardcoded file paths.
- **Why:** Protects against misconfiguration, crashes early on invalid parameters, and dynamically resolves paths relative to the project root.
- **How it works:** Loads validated environment variables with constraints (e.g. port range, batch size ceilings) and auto-creates the isolated local data directory.
- **How it helps here:** Ensures portability across local machines, Docker containers, and free-tier cloud hosts without modifying code.
- **Alternatives considered:** Manual `os.getenv` lookups (rejected: no validation, silent type conversion failures, no default guarantees).

### Component: Request Correlation & PII-Safe Logging (`backend/app/middleware.py` & `backend/app/logging.py`)
- **What it is:** ContextVar-driven HTTP middleware and JSON log formatter that injects `X-Request-ID` headers into every response and redacts candidate personal data from logs.
- **Why:** Delivers end-to-end request traceability while honoring data privacy by preventing applicant emails and phone numbers from being exposed in logs.
- **How it works:** Intercepts requests, generates or preserves UUIDs, instruments response times, and passes messages through regex scrubbers before outputting JSON.
- **How it helps here:** Debugging asynchronous batch candidate runs becomes deterministic without risking GDPR/privacy leaks in logs.
- **Alternatives considered:** Standard unformatted console printing (rejected: impossible to correlate logs across concurrent async requests; risks logging candidate PII).

### Component: FastAPI Core Application & 4xx Guardrails (`backend/app/main.py`)
- **What it is:** FastAPI application instance featuring CORS controls, lifespan management, uptime health checks (`/health`, `/api/v1/ping`), and strict 4xx exception handlers.
- **Why:** Guarantees that bad client requests or malformed payloads always yield structured 4xx responses (HTTP 422/404/400) and never leak unhandled 500 server crashes.
- **How it works:** Registered custom exception handlers intercept `RequestValidationError` and `HTTPException`, returning structured JSON alongside the active `request_id`.
- **How it helps here:** Robust API contract ensures frontend recruiter screens handle input errors gracefully without unexpected disconnects.
- **Alternatives considered:** Default unformatted FastAPI exceptions (rejected: inconsistent schema, missing request ID correlation for clients).

### Component: Frontend React Client & Testing Suite (`frontend/`)
- **What it is:** Vite + React + TypeScript application adhering to strict compiler rules, keyboard accessibility standards, and Vitest component verification.
- **Why:** Delivers an interactive recruiter dashboard with labelled inputs, keyboard navigation, and explicit loading, empty, and error state handling on all views.
- **How it works:** Built with vanilla CSS design tokens, ESLint 9 flat configuration, strict TypeScript flags, and accessibility-first Testing Library suites.
- **How it helps here:** Serves as the recruiter-facing workspace for uploading resumes, inspecting cited evidence, and executing hiring workflow decisions without heavy frameworks.
- **Alternatives considered & Architectural Correction:** Streamlit UI (rejected: limited keyboard accessibility). Note: The initial shell was bootstrapped with vanilla CSS; however, per decision correction, Batch 5 will migrate the client to **Tailwind CSS + shadcn/ui** to provide robust, accessible data tables, dialogs, drag-and-drop boards, and charts required for the 17 recruiter screens.

### Component: Quality Tooling & Automated CI Pipeline (`.pre-commit-config.yaml`, `.github/workflows/ci.yml`, `scripts/`)
- **What it is:** Pre-commit hooks for secret detection and linting, developer helper scripts (`scripts/run_checks.sh`), and GitHub Actions CI pipelines executing on free Ubuntu runners.
- **Why:** Prevents secret leaks before code leaves the local machine and guarantees every PR and commit on `main` satisfies quality bars (Ruff, Mypy, Pytest >=80% coverage, ESLint, TypeScript compilation, Vitest, Gitleaks).
- **How it works:** Git hooks trigger Gitleaks and Ruff; GitHub Actions workflow provisions isolated free runners for parallelized backend, frontend, and secret scanning jobs.
- **How it helps here:** Enforces the stop-the-line security rule and ensures zero regressions enter the codebase as new agents and features are introduced.
- **Alternatives considered:** Manual developer checks without automated CI (rejected: high risk of undetected broken builds, missing tests, or exposed tokens).

### Component: Project Entry Documentation (`README.md`)
- **What it is:** The root repository documentation covering platform capabilities, monorepo directory layout, developer prerequisites, setup guides, and test execution commands.
- **Why:** Provides clear orientation for any developer, reviewer, or user running the repository locally for the first time.
- **How it works:** Explains step-by-step onboarding using both automated scripts and manual CLI workflows for backend and frontend.
- **How it helps here:** Eliminates ambiguity around dependencies, port bindings, and verification commands.
- **Alternatives considered:** Minimal or auto-generated boilerplate readme (rejected: fails to communicate project context, architecture, and verification instructions).

### Component: Stratified Dataset Sampling & Gold Pairs Baseline (`docs/eval_pairs_locked.json`)
- **What it is:** A locked benchmark set of 34 verified query-chunk pairs, alongside a stratified sample of 300 real resumes across 24 professional domains and 2,000 sampled LinkedIn job postings.
- **Why:** Establishes a concrete, repeatable baseline for measuring retrieval performance (Hit@1/3/5/10 and MRR) and parser quality without committing bulky datasets to version control.
- **How it works:** Preserves exact ground truth query targets while isolating binary PDFs and CSVs in local gitignored storage (`data/`).
- **How it helps here:** Enables rigorous truth testing and benchmark evaluations across sparse (BM25), dense (MiniLM/BGE), and hybrid retrieval architectures.
- **Alternatives considered:** Generating synthetic test resumes (rejected: fails to replicate multi-column layouts, OCR artifacts, and unstructured phrasing found in real resumes).

### Component: SSRF-Protected Job Description Scraper (`backend/app/core/jd_scraper.py`)
- **What it is:** Robust HTTP client and HTML extractor for acquiring online job postings with strict SSRF defenses, timeouts, and body size limits.
- **Why:** Protects internal infrastructure and cloud environments against Server-Side Request Forgery (SSRF) when recruiters input arbitrary job posting URLs.
- **How it works:** Validates schemes (`http`/`https`), resolves DNS before socket connection, and rejects private, loopback, link-local, multicast, and cloud metadata addresses (e.g. AWS `169.254.169.254`). Enforces a 10s connect timeout and a 2 MB streaming body limit. Falls back to selector-based and semantic article HTML parsers.
- **How it helps here:** Allows recruiters to paste job URLs directly without risking attacks on internal cloud credentials or intranet microservices.
- **Alternatives considered:** Raw `requests.get` or `urllib.request` (rejected: completely vulnerable to SSRF, cloud credential theft, and denial-of-service via huge payloads).

### Component: Structured Experience & Education Extractors (`backend/app/core/experience_extractor.py` & `education_extractor.py`)
- **What it is:** Deterministic rule-based extractors for parsing candidate titles, employers, dates, bullet accomplishments, degree hierarchies (including B.Tech/M.Tech/MCA/Dipl.-Ing.), graduation years, and career gaps.
- **Why:** Solves closed-vocabulary and structural extraction problems deterministically and cheaply without burning costly, slow LLM inference tokens.
- **How it works:** Uses regex patterns, seniority level mappings (0-4), date interval difference calculation for employment spans and career gaps ($\ge 6$ months), and title/company disambiguation heuristics that preserve clean titles.
- **How it helps here:** Feeds downstream retrieval and scoring agents with verified job title progressions, total experience metrics, and education ordinal ranks with zero LLM hallucination risk.
- **Alternatives considered:** Zero-shot LLM parsing for every resume (rejected: slow, expensive, non-deterministic, and prone to hallucinations on dates and titles).

### Component: Multi-Column Resume PDF Parser & Deterministic Gate (`backend/app/core/pdf_parser.py` & `scripts/measure_parser.py`)
- **What it is:** Production PDF extraction engine with horizontal coordinate clustering for multi-column resumes, deterministic gate verification, confidence estimation, and PII isolation.
- **Why:** Multi-column PDFs scramble text reading order in standard parsers; ATS systems frequently fail on non-resume uploads or leak PII into scoring text.
- **How it works:** Uses `pdfplumber` character geometry to cluster columns with fallback to `pypdf`. Applies a deterministic rule-based gate scoring 8 resume markers vs negative document markers (invoices, papers, contracts). Isolates candidate contact details into a distinct `ContactPII` container and produces scrubbed `scoring_text`.
- **How it helps here:** Measured on 100 real resumes and 20 non-resumes: achieved **98.0% clean title extraction** (jumping from old 33.3% baseline), **100% gate recall**, **100% gate precision**, and **0.0% parse failures**.
- **Alternatives considered:** OCR-based layout analysis (rejected: excessive memory footprint exceeding the 400 MB RAM budget); unseparated PII in scoring text (rejected: violates privacy rules and biases scoring).
