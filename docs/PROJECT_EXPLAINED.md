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

### ONNX Runtime & Tokenizers (Quantized CPU Inference)
- **What it is:** High-performance inference engine running quantized Transformer neural networks directly on CPU without PyTorch.
- **Why chosen:** Keeps process RSS memory under 150 MB (MiniLM-L6 measured at 132.3 MB RSS, +51.7 MB delta) compared to PyTorch which consumes 750-980 MB, easily exceeding Render/free-tier memory ceilings.
- **How it helps here:** Generates L2-normalized 384-dimensional dense vectors for semantic candidate chunk retrieval in ~74 ms per chunk.
- **Alternatives considered:** PyTorch + `sentence-transformers` (rejected: pulls heavy torch wheels, bloated Docker images, and exceeds RAM limits); cloud embedding APIs (rejected: costs money and violates self-hosted privacy constraints).

### bm25s (In-Memory Lexical Search)
- **What it is:** Ultra-fast, pure-Python/NumPy implementation of the BM25 lexical ranking algorithm.
- **Why chosen:** Sub-millisecond in-memory indexing and querying per candidate, zero SQLite lock contention, and zero native binary baggage.
- **How it helps here:** Serves as the primary retrieval signal, achieving 100% Hit@5 and 0.8456 MRR on the locked evaluation set.
- **Alternatives considered:** Full-text database engines like SQLite FTS5 or Elasticsearch (rejected: SQLite FTS lacks isolated ephemeral scoring flexibility; Elasticsearch requires gigabytes of Java RAM).

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
- **How it works:** Preserves exact ground truth query targets while isolating binary PDFs and CSVs in local gitignored storage (`data/`). Measured the LinkedIn job posting dataset (`linkedin_jobs_clean.csv`), confirming the true row count is **123,700 rows across 31 columns** (the legacy vault manifest's claim of 1.3 million rows was an unmeasured estimate).
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

### Component: Multi-Column Resume PDF Parser & Deterministic Gate (`backend/app/core/pdf_parser.py` & `scripts/measure_parser.py`, `scripts/measure_parser_audit.py`)
- **What it is:** Production PDF extraction engine with horizontal coordinate clustering for multi-column resumes, deterministic gate verification, confidence estimation, and PII isolation.
- **Why:** Multi-column PDFs scramble text reading order in standard parsers; ATS systems frequently fail on non-resume uploads or leak PII into scoring text.
- **How it works:** Uses `pdfplumber` character geometry to cluster columns with fallback to `pypdf`. Applies a deterministic rule-based gate scoring 8 resume markers vs negative document markers (invoices, papers, contracts). Isolates candidate contact details into a distinct `ContactPII` container and produces scrubbed `scoring_text`.
- **Parser Accuracy & Gate Audit Results:**
  - **Unseen Resumes Audit (40 random resumes outside first 100 tuning set):** Generated [`data/parser_audit_40.csv`](file:///home/sajad/PROJECTS/RECRUIT-LENS/data/parser_audit_40.csv) containing 291 extracted experience rows. Automated heuristic audit showed **254/291 entries (87.3%)** are valid, clean job titles and companies with plausible date ranges (replacing the previous non-empty 98% proxy).
  - **Gate Precision Audit (20 fresh non-resumes):** Evaluated against 5 real job descriptions from `jds_sample_2000.csv`, 5 cover letters, 4 meeting minutes, 3 product brochures, and 3 certificates. Achieved **95.0% gate precision** (19/20 correctly rejected); observed 1 false positive (`cover_letter_1.pdf` at gate confidence 0.60 due to strong employment phrasing). 0.0% parse failures across all documents.
- **Alternatives considered:** OCR-based layout analysis (rejected: excessive memory footprint exceeding the 400 MB RAM budget); unseparated PII in scoring text (rejected: violates privacy rules and biases scoring).

### Component: Section-Aware Resume & JD Sliding-Window Chunkers (`backend/app/core/resume_chunker.py` & `jd_chunker.py`)
- **What it is:** Granular sliding-window text chunkers for candidate resumes and job descriptions maintaining section provenance and metadata.
- **Why:** Full resumes are too broad for dense semantic retrieval; small disjoint fragments lose job context. Section-aware chunking preserves coherent accomplishments with optimal retrieval density.
- **How it works:** Applies configured sliding windows: Experience and Projects (200 words, 40-word overlap); Skills, Education, and Summary (150 words, 20-word overlap); JD query chunking (100 words, 20-word overlap). Every chunk retains `section`, `resume_id`/`jd_id`, and `word_count`.
- **How it helps here:** Produces high-signal text chunks that enable sub-second BM25 and semantic matching while providing exact citation targets for generated candidate reviews.
- **Alternatives considered:** Fixed-length character chunking (rejected: splits words and bullet points arbitrarily across sentences).

### Component: Quantized ONNX Dense Embedder & Model Benchmark (`backend/app/core/embeddings.py` & `scripts/evaluate_truth_and_embedders.py`)
- **What it is:** Pure-ONNX Runtime embedding singleton behind an abstract `BaseEmbedder` interface, with offline model weight caching in `data/hf_cache/`.
- **Why:** PyTorch dependencies consume 750-980 MB of RAM, instantly breaching the 400 MB backend RSS budget. Quantized ONNX with CPU memory arena disabled keeps inference lightweight, deterministic, and within budget.
- **How it works:** Tokenizes with fast Rust-based `tokenizers`, executes 8-bit quantized ONNX models on CPU with 2 execution threads and `enable_cpu_mem_arena = False`, performs weighted mean pooling with attention masks, and outputs unit-length L2-normalized float32 vectors (dim=384).
- **Benchmark & Model Selection Result (Fresh Isolated Processes, Arena Disabled, MaxLen=256, Batch=16):**
  - **MiniLM-L6 (quantized ONNX):** 101.3 MB initial RSS, 152.1 MB loaded RSS, **164.2 MB peak RSS**, **5.05 ms/chunk** latency. Within-Resume Hit@5: 82.4%, MRR: 0.6412. Corpus-Wide Hit@5: **38.2%**, MRR: **0.2574**.
  - **BGE-small (quantized ONNX):** 101.3 MB initial RSS, 170.2 MB loaded RSS, **178.7 MB peak RSS**, **8.39 ms/chunk** latency. Within-Resume Hit@5: 82.4%, MRR: 0.4794. Corpus-Wide Hit@5: **14.7%**, MRR: **0.1312**.
  - **Decision:** **MiniLM-L6 is retained.** While BGE-small now fits comfortably under the 350 MB cap (178.7 MB) with the memory arena disabled, MiniLM soundly outperforms BGE on both Hit@5 (38.2% vs 14.7%) and MRR (0.2574 vs 0.1312) in corpus-wide retrieval, while running 1.66x faster.
- **Alternatives considered:** SentenceTransformers / PyTorch (rejected: 750-980 MB RSS); raw unquantized FP32 ONNX (rejected: larger disk footprint and slower CPU throughput).

### Component: Candidate-Isolated Hybrid Retrieval Engine & Truth Test (`backend/app/core/retrieval.py` & `scripts/evaluate_truth_and_embedders.py`)
- **What it is:** Candidate-isolated hybrid search engine combining in-memory BM25 lexical search (`bm25s`) and in-memory cosine dot-product dense retrieval via Reciprocal Rank Fusion (RRF $k=60$).
- **Why:** Eliminates the overhead and concurrency locking of ChromaDB for per-candidate searches while strictly guaranteeing zero cross-candidate data leakage.
- **Candidate Pool Analysis & Random Guess Baseline:**
  - Evaluated on 34 gold evaluation queries mapped to chunks from the newly built `resume_chunker`.
  - Candidate pool size per query: **Min = 4, Median = 8, Max = 16, Mean = 8.7 chunks per resume**.
  - Random Guess Baseline for this candidate pool: **Hit@5 = 62.92%**, **Hit@10 = 95.34%**, **MRR = 0.3381**. (Explains why within-resume retrieval achieves elevated hit rates: a median pool of 8 chunks naturally inflates Top-5 selection chances under random sampling).
- **Within-Resume Retrieval Test (34 Remapped Gold Queries across Single-Candidate Chunks):**
  - **BM25:** Hit@1: 44.1%, Hit@3: 88.2%, Hit@5: 94.1%, Hit@10: 97.1%, MRR: **0.6395**.
  - **Dense (MiniLM):** Hit@1: 50.0%, Hit@3: 76.5%, Hit@5: 82.4%, Hit@10: 97.1%, MRR: **0.6412**.
  - **Hybrid (MiniLM RRF $k=60$):** Hit@1: 55.9%, Hit@3: 85.3%, Hit@5: 88.2%, Hit@10: 97.1%, MRR: **0.6913**.
- **Corpus-Wide Retrieval Test (34 Gold Queries across All 300 Resumes Pooled = 2,318 Chunks):**
  - **BM25:** Hit@1: 23.5%, Hit@3: 47.1%, Hit@5: **47.1%**, Hit@10: **70.6%**, MRR: **0.3702**.
  - **Dense (MiniLM):** Hit@1: 14.7%, Hit@3: 38.2%, Hit@5: 38.2%, Hit@10: 44.1%, MRR: 0.2574.
  - **Hybrid (MiniLM RRF $k=60$):** Hit@1: 20.6%, Hit@3: 38.2%, Hit@5: 47.1%, Hit@10: 61.8%, MRR: 0.3283.
  - **Comparison with Old Project (64.7% Hit@5):** The old project tested 100 queries across a different corpus and chunk size. In our 2,318-chunk corpus across 34 queries, BM25 achieves 47.1% Hit@5 and 70.6% Hit@10; MiniLM dense achieves 38.2% Hit@5.
  - **Architectural Decision:** In the corpus-wide test, BM25 achieves 47.1% Hit@5 and 0.3702 MRR, outperforming Dense MiniLM (38.2% Hit@5, 0.2574 MRR) and beating Hybrid on MRR (0.3702 vs 0.3283) and Hit@10 (70.6% vs 61.8%). Per rule criteria, **BM25 remains the primary retrieval signal**, with dense semantic search providing secondary recall support.
- **Alternatives considered:** Ephemeral ChromaDB collections per candidate (rejected: high memory allocation churn and SQLite metadata contention in batch loops).

### Component: Interactive Pair Annotation CLI (`scripts/label_pairs.py`)
- **What it is:** Command-line annotation tool for expanding the locked evaluation set by presenting queries and candidate resume chunks for rapid binary relevance judgment (`[y/n/s/q]`).
- **Why:** Allows developers and recruiters to continuously expand ground-truth evaluation pairs across new job categories without blocking batch execution.
- **How it works:** Iterates through local chunk files, prompts for queries and domains, displays candidate text previews, and appends valid positive pairs (`relevance_score: 2`) to `docs/eval_pairs_labeled.json`.
- **How it helps here:** Provides a non-blocking workflow to grow $N$ beyond 34 pairs to narrow bootstrap confidence intervals over time.
- **Alternatives considered:** Manual JSON editing (rejected: error-prone, slow, and risks syntax formatting bugs).

### Component: Curated Skill Taxonomy & Inference Engine (`backend/app/core/taxonomy.py` & `backend/app/data/skills_taxonomy.json`)
- **What it is:** Production skill extraction, alias canonicalization, and relationship-based skill inference engine backed by the official O*NET 29.0 Technology Skills database (8,754 canonical skills, 8,799 alias mappings, 134 taxonomy families).
- **Why:** Solves open-vocabulary and synonym-heavy skill matching deterministically without burning slow, expensive LLM calls. Provides standardized canonical skill identities and hierarchical inference relations.
- **How it works:** Tokenizes and applies length-prioritized regex pattern matchers with strict word boundaries to eliminate false positive substring collisions. Maps aliases (e.g., `k8s -> Kubernetes`, `py -> Python`, `js -> JavaScript`, `ml -> Machine Learning`) to canonical forms and infers underlying skills with calibrated confidence scores (e.g. `Django` implies `Python` at 0.95 confidence; `Kubernetes` implies `Docker` at 0.85 confidence).
- **How it helps here:** Enables deterministic, sub-millisecond skill extraction for both job requirements and resumes, tracking exact character offset provenance for citation verification.
- **Alternatives considered:** Zero-shot LLM entity extraction for every candidate (rejected: slow, nondeterministic, prone to hallucinating non-existent skills); uncurated string substring matching (rejected: catastrophic false positive rate matching 'js' in 'jobs' or 'py' in 'copy').

### Component: Job Description Requirement Extractor (`backend/app/core/jd_requirements.py`)
- **What it is:** Deterministic extractor segmenting job postings into structured requirements: minimum/maximum years of experience, minimum education degree rank (0-4), and partitioned must-have vs nice-to-have skill sets.
- **Why:** Downstream candidate scoring and tier assignment depend on unambiguous classification of mandatory requirements (where missing must-haves disallow top tiers) versus secondary preferences.
- **How it works:** Identifies semantic section boundaries (`Requirements`, `Basic Qualifications`, `Preferred`, `Bonus`), regex patterns for numerical experience spans, degree ordinal hierarchies (Doctorate 4 down to High School 0), and linguistic cue words (`must`, `required`, `essential`, `plus`, `bonus`, `nice to have`). Maps extracted keywords to canonical taxonomy entities. Leaves an explicit interface hook for optional LLM refinement in Batch 3.
- **How it helps here:** Provides validated, typed `JobRequirements` instances guaranteeing consistent input shapes for candidate feature extraction and metamorphic testing.
- **Alternatives considered:** LLM extraction for all JDs (rejected: violates the zero-cost offline rule and introduces latency/nondeterminism on standard requirement fields).

### Component: Resume Skill Extractor with Citation Evidence & Taxonomy Inference (`backend/app/core/skill_extractor.py`)
- **What it is:** Entity extraction engine matching candidate resume chunks to canonical skills, recording character-level snippet citations (`chunk_id`, section, offsets), and deriving inferred skills with calibrated confidence scores (e.g. Django implies Python at 0.95 confidence).
- **Why:** Every extracted skill claim must carry exact textual provenance for human inspection and Self-RAG critique, while capturing framework-language implications (a candidate who built Django apps knows Python even if the word 'Python' was omitted in that bullet).
- **How it works:** Scans section chunks with word-boundary regex matchers from `SkillTaxonomy`. Tracks character spans and surrounding sentence context snippets for each occurrence. Applies taxonomy inference relations with explicit match precedence (explicit matches always take 1.0 confidence). Protects against keyword stuffing by tracking occurrence counts while deduplicating canonical skill identities.
- **How it helps here:** Supplies downstream feature extractors with verified `CandidateSkillsResult` structures separating explicit from inferred skills with citation evidence.
- **Alternatives considered:** Naive string matching without chunk offsets (rejected: violates the core non-negotiable rule that every claim must link to cited evidence).

### Component: Bounded Candidate Feature Extractor with Keyword Stuffing Guard (`backend/app/core/features.py`)
- **What it is:** Candidate-to-job feature engineering pipeline computing 10 explainable, bounded comparison features (`must_have_coverage`, `nice_to_have_coverage`, `matched_must_count`, `matched_nice_count`, `inferred_count`, `missing_must_count`, `years_gap`, `seniority_gap`, `education_match`, `title_match`, `skill_recency`, `dense_similarity`).
- **Why:** Machine learning and scoring models require strictly bounded numerical inputs with calibrated confidence and explicit missing-data provenance so missing inputs never silently act as zero.
- **How it works:**
  - Every feature is wrapped in a `FeatureValue` object with strict `[min_bound, max_bound]`, calibrated confidence (0.0 to 1.0), and boolean `is_missing` flags with human-readable explanations when data is absent.
  - **Keyword Stuffing Guard:** Evaluates skill coverage as a set-level match per canonical taxonomy skill. A candidate mentioning 'Python' 50 times receives the exact same coverage and matched count as a candidate mentioning it once.
  - **Missing Data Handling:** If a candidate's resume lacks dates, `years_gap` is explicitly marked `is_missing=True` with `missing_reason="Candidate experience dates could not be parsed"` rather than silently penalizing the candidate with 0.
  - Computes title similarity via token overlap and seniority level gap via ordinal distance (-4 to +4).
- **How it helps here:** Serves as the immutable feature foundation for both baseline linear scoring and monotonic XGBoost ranking models.
- **Alternatives considered:** Raw unnormalized feature dictionaries (rejected: lack bounds checking, hide missing-data errors, and vulnerable to keyword manipulation).

### Component: Weak-Supervision Pair Dataset Generator (`scripts/build_weak_supervision.py`)
- **What it is:** Dataset synthesis pipeline crossing 120 diverse candidate resumes (5 per category across all 24 occupational categories) with 105 representative job descriptions across 11 macro occupational families. Produces 1,080 graded candidate-job pairs (`data/weak_supervision_pairs.json`).
- **Why:** Machine learning ranking models and tier threshold calibration require thousands of graded candidate-job pairs without incurring hundreds of hours of manual annotation or relying on costly LLM labelers.
- **How it works:**
  - Classifies JDs and resumes into macro occupational families (e.g. Technology & Engineering, Finance & Accounting, Healthcare & Wellness, Legal & Compliance).
  - Generates three distinct pair regimes:
    1. **Positives (480 pairs):** Candidate and job from the same functional family, graded primarily by must-have skill coverage ($C_{\text{must}}$), nice-to-have bonus, experience gap penalty, and title overlap.
    2. **Hard Negatives (360 pairs):** Candidate and job from adjacent functional families (e.g., Tech paired with Digital Media/Creative or Sales; Finance paired with Legal or HR).
    3. **Easy Negatives (240 pairs):** Candidate and job from completely disjoint families (e.g., Chef paired with IT Engineer; Healthcare nurse paired with Accountant).
  - Assigns continuous proxy scores $y \in [0.0, 1.0]$ and discrete recruitment tiers (0=Reject: 652, 1=Hold: 341, 2=Interview: 70, 3=Strong Fit: 17).
- **Documented Limitations & Honest Boundaries:**
  - *Proxy Labels, Not Hiring Outcomes:* Labels are automated heuristic proxies based on occupational alignment and deterministic requirement coverage. They do not capture soft skills, interview presence, culture fit, or real-world hiring outcomes.
  - *Conservative Strong Fit Bar:* Only 1.6% (17 / 1,080) achieve Tier 3 ("Strong Fit"), enforcing strict must-have skill coverage ($\ge 80\%$) and no significant experience deficit.
- **Alternatives considered:** Zero-shot LLM labeling (rejected: violates zero-cost offline principle, introduces hallucination risks, and produces inconsistent label distributions); random pair sampling without family structure (rejected: yields $>95\%$ trivial negatives with zero hard boundaries).

### Component: Explainable Candidate Scoring Engine & Grouped Cross-Validation (`backend/app/core/scoring.py` & `scripts/train_and_eval_models.py`)
- **What it is:** Candidate scoring engine implementing two transparent scoring paradigms:
  1. `WeightedBaselineScorer`: Deterministic, additive linear combination with dynamic missing-data reweighting.
  2. `MonotonicXGBoostScorer`: Gradient boosted decision trees trained with strict monotonic constraints (`monotone_constraints=(1, 1, 1, 1, 1, -1, 1, 0, 1, 1, 1, 1)`), guaranteeing that acquiring more must-have skills or longer relevant tenure never lowers candidate score.
- **Why:** Scoring NEVER uses an LLM. It must be deterministic, non-discriminatory, mathematically explainable, and provably monotonic with respect to qualifications.
- **Grouped Cross-Validation Benchmark (5-Fold GroupKFold grouped by `resume_id`):**
  - **Weighted Baseline:**
    - NDCG@5: **0.9144**, NDCG@10: **0.9255**
    - Spearman Rank Correlation ($\rho$): **0.3575**
    - MAE: **0.1736**, RMSE: **0.2164**
    - Expected Calibration Error (ECE): **0.1196**
  - **Monotonic XGBoost:**
    - NDCG@5: **0.9303** (+0.0159 delta)
    - NDCG@10: **0.9406** (+0.0151 delta)
    - Spearman Rank Correlation ($\rho$): **0.4463** (**+0.0888 delta**, beats baseline by a wide margin $> 0.03$)
    - MAE: **0.1484** (-0.0252 error reduction)
    - Expected Calibration Error (ECE): **0.0191** ($6\times$ superior probability calibration)
- **Model Decision:** Monotonic XGBoost achieved a **+0.0888 Spearman Rho gain** and superior calibration (ECE 0.0191 vs 0.1196), easily clearing the $\ge 0.03$ margin requirement. Monotonic XGBoost is shipped as the primary ranking model (`backend/app/data/scoring_xgb.json` at 106 KB), with Weighted Baseline retained for zero-dependency instant fallback.
- **Alternatives considered:** Linear regression without missing-data handling (rejected: silently penalizes missing dates as 0); unconstrained neural network or Deep Ranker (rejected: non-monotonic, non-interpretable, high RAM consumption).
