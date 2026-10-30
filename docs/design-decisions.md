# Recruit Lens Frontend Design Decisions & Rationales

This document records the foundational product and architectural design choices implemented in the Recruit Lens frontend interface.

---

## 1. Prestige Bias Suppression by Design
- **Decision:** Employer and company names are completely suppressed from candidate lists, tables, and overview cards. The table displays only the candidate's verifiable job title (e.g., "Senior Distributed Systems Engineer").
- **Rationale:** Studies in hiring fairness demonstrate that brand-name employer prestige (e.g. FAANG vs. unknown startups) introduces heavy cognitive bias that obscures verifiable technical competency. Scoring is grounded strictly in demonstrated skills and resume evidence.
- **Implementation:** Explicit table header `Most recent role (Title only)`, persistent dismissible prestige notice banner, and zero employer columns across all views.

---

## 2. Global Blind Screening Mode
- **Decision:** Global navbar switch (`role="switch"`, `aria-checked`) toggles Blind Mode across all views in real time.
- **Rationale:** Provides recruiters and hiring managers an instant, audit-compliant method to evaluate candidates without exposure to demographic markers, full names, personal emails, or locations.
- **Implementation:** When Blind Mode is ON, candidate identifiers are masked to `Candidate #NNNN` (e.g. `Candidate #6299`) with a lock icon. Contact details and locations are redacted across candidate tables, dossiers, pipeline cards, and email recipient fields.

---

## 3. Evidence-Grounded Briefings & Bi-directional Citation Highlighting
- **Decision:** Every AI statement in the recruiter briefing contains an inline citation pill (e.g. `[c_01]`, `[c_02]`).
- **Rationale:** Eliminates LLM hallucination risk and creates recruiter trust by linking every analytical claim to verbatim evidence from the candidate's resume.
- **Implementation:** Clicking a citation pill focuses and scrolls the verbatim resume evidence viewer directly to that chunk, highlighting it with border and background rings. For assistive technologies, an `aria-live="polite"` region announces the focused chunk and text snippet.

---

## 4. Two-Step Human Review Gate for Communications
- **Decision:** AI drafts communications, but email delivery is strictly locked behind a two-step human approval gate.
- **Rationale:** Autonomous email delivery by AI agents presents high organizational and legal risk. Human recruiters must verify candidate messaging.
- **Implementation:**
  - Step 1 button: `1. Approve Draft`.
  - Step 2 button: `2. Send Email` (remains disabled and locked with `<Lock />` until Step 1 is executed).
  - **Edit Invalidation Rule:** If the recruiter edits the textarea after approval, Step 2 immediately locks again, revoking approval to ensure that unreviewed edits can never be dispatched.
  - **Default Safety:** "Dry-run (no live send)" checkbox is enabled by default.

---

## 5. Adverse Action Compliance: Score-Free Rejection Drafts
- **Decision:** Rejection emails are strictly prohibited from referencing numerical scores, percentages, or rank numbers (e.g., "42/100", "Top 10%").
- **Rationale:** Exposing automated algorithmic scoring numbers in adverse action notices creates confusion, disputes, and potential compliance liabilities under hiring regulations (e.g., NYC Local Law 144, EU AI Act).
- **Implementation:** Rejection templates focus exclusively on qualitative business priorities. The editor includes a regex validation monitor that alerts the user and disables the "Approve Draft" button if numerical score patterns are entered.

---

## 6. What-If Score Simulator Guardrail
- **Decision:** The What-If simulator allows recruiters to explore hypothetical score changes (e.g., +5 pts for Cassandra experience) while displaying a prominent, non-dismissible warning.
- **Rationale:** Recruiters need to assess sensitivity to requirements, but hypothetical numbers must never contaminate official evaluation logs.
- **Implementation:** Real-time delta calculations (`Simulated score: 95 → 100 ▲ +5`), one-click reset button, and mandatory banner: *"Hypothetical simulation. Never saved to candidate record."*

---

## 7. Pipeline Kanban Stage Advancement Guardrail
- **Decision:** Moving a candidate with a Reject-tier match score ($< 55$) into the "Offer" column triggers an immediate justification modal.
- **Rationale:** Protects hiring pipelines from accidental misplacement or unrecorded overrides, creating an immutable compliance trail.
- **Implementation:** An overlay dialog requires the recruiter to input a rationale for advancing the low-scoring candidate before the stage transition is committed.
