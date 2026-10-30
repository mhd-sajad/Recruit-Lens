# Recruit Lens Open Architecture Questions & Recommended Defaults

This document tracks technical and product questions surfaced during frontend implementation, along with recommended engineering defaults.

---

### Question 1: Requisition Deactivation & Data Retention
- **Context:** When a job requisition is closed or filled, should candidate evaluations and uploaded CV text be purged or archived?
- **Tradeoffs:**
  - *Option A (Hard Purge):* Minimizes disk footprint and GDPR data retention exposure, but destroys evidence needed if hiring decisions are audited later.
  - *Option B (Soft Archive with Immutable Audit Trail - Recommended):* Mark requisition as `Closed`; retain cryptographic hash records, anonymized scoring logs, and citations; redact raw PDF binaries after 90 days.
- **Recommended Default:** Option B. Legally defensible auditability requires preserving the scoring decision trail, while automatic raw binary purging respects storage and privacy limits.

---

### Question 2: Automatic Re-Ranking on Weight Adjustments vs. Manual Trigger
- **Context:** When a recruiter edits skill weights in Step 2 of the Requisition wizard or in job settings, should existing candidates be re-ranked immediately in real time?
- **Tradeoffs:**
  - *Option A (Automatic Live Re-Ranking):* Immediate feedback, but can lead to confusion if candidate rank orders shift while recruiters are actively reviewing dossiers or drafting emails.
  - *Option B (Manual Recalculation Trigger with Diff Preview - Recommended):* Show a banner *"Scoring criteria modified. 14 candidates pending re-score."* with a "Recalculate Batch" button and rank shift diff preview.
- **Recommended Default:** Option B. Prevents unexpected changes during active review workflows and ensures recruiters can review the impact of weight adjustments deliberately.

---

### Question 3: Multi-Recruiter Concurrent Email Drafting
- **Context:** In large talent acquisition teams, two recruiters might open the same candidate's email draft simultaneously.
- **Tradeoffs:**
  - *Option A (Pessimistic Drafting Lock):* Only one user can open the email modal at a time. High friction in fast-paced hiring rounds.
  - *Option B (Optimistic Concurrency with Invalidation - Recommended):* Allow concurrent viewing; if User A approves or edits a draft, User B receives a prompt to refresh. Step 2 (Send) always validates that the current text matches the approved revision hash.
- **Recommended Default:** Option B. Preserves flexibility while guaranteeing that modified text cannot bypass human review.

---

### Question 4: PII Reveal Auditing
- **Context:** In Blind Screening Mode, when an authorized hiring manager clicks to reveal a candidate's full name and email for an interview, should this action be logged?
- **Tradeoffs:**
  - *Option A (Silent Reveal):* Low friction for the recruiter.
  - *Option B (Audited Reveal Event - Recommended):* Record an immutable audit log entry: `Privacy: Blind Mode Reveal (Candidate #6299 revealed by user@company.com at Timestamp)`.
- **Recommended Default:** Option B. Enforces organizational accountability and discourages unnecessary unmasking prior to stage advancement.
