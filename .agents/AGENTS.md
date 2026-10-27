# Project-Scoped Rules for Recruit Lens

The following operating principles must be followed strictly:

1. **VERIFY, DON'T JUST ASSERT.** When you say something is "done," "fast," "safe," or "validated," back it with the actual number, test output, or benchmark that proves it — not a description of what should be true. If you haven't measured something, say so explicitly instead of implying it's fine.

2. **TREAT SECURITY AS STOP-THE-LINE, NOT A FOOTNOTE.** If you find a credential, a secret, an exposed key, or anything similar, stop what you're doing, report it immediately and completely (including anywhere it might have propagated — other remotes, forks, caches, deploys), and wait for confirmation before continuing. Don't bury it in a status update alongside unrelated progress.

3. **QUESTION A DESIGN BEFORE YOU BUILD ON TOP OF IT.** Before the next agent/module depends on a previous one's output, sanity-check that previous piece for hidden costs: does it scale linearly, does it have a failure mode under load, is there an edge case nobody's tested. Raise this before it's buried under three more layers of code.

4. **MATCH THE TOOL TO THE PROBLEM'S ACTUAL SHAPE.** Closed-vocabulary, well-patterned problems (years of experience, seniority titles, structural JD fields) should be solved with regex/rules/lookup tables — fast, deterministic, testable. Open-vocabulary, synonym-heavy problems (skills, free-text resume language) need embedding-based or taxonomy-backed matching, not plain string matching. Don't reach for an LLM call where a deterministic rule works, and don't reach for regex where the problem is genuinely open-ended. If you're not sure which kind of problem you're facing, say so and propose both options with the tradeoff, rather than silently picking one.

5. **RAG GROUNDING IS NON-NEGOTIABLE.** Every piece of generated text (explanations, interview questions, email drafts) must trace back to retrieved evidence chunks. If you're about to generate something without a retrieval step feeding it, stop and add the retrieval step first.

6. **WORK IN SMALL, REVIEWABLE INCREMENTS.** Commit and push after every individual working piece, not after a whole feature is finished. Write the test before or alongside the code, not after. This makes each change independently reviewable and independently revertable if something's wrong.

7. **WHEN REPORTING PROGRESS, INCLUDE WHAT COULD BE WRONG, NOT JUST WHAT WORKS.** After finishing something, explicitly list untested edge cases, known limitations, or things you're assuming rather than have verified. A report that only lists successes is incomplete — the failure modes are as important as the passing tests.

8. **DEFAULT SENSIBLY ON NARROW CHOICES, BUT SURFACE GENUINE TRADEOFFS.** For small implementation details with one clearly reasonable answer, just pick it and move on. For real architectural forks (e.g., "should this scale later" or "which library"), lay out 2-3 options with what each costs/gains, rather than picking silently or asking a vague open question.

9. **DON'T LET "IT WORKS" SUBSTITUTE FOR "IT'S REVIEWED."** Finishing a build step is not the same as it being approved to move forward on. Always pause for review at the checkpoints defined in the project instructions, even if everything passed locally.

10. **KEEP PROJECT_EXPLAINED.md LIVING.** Every time a new commit adds something meaningful (a new agent, a new feature, a new integration, a fix to something significant), you MUST add a new entry to Section 4 of docs/PROJECT_EXPLAINED.md using the exact template defined there BEFORE moving on to the next piece of work. If Section 1, 2, or 3 needs updating because something changed, update those too and note briefly what changed and why. This is part of what 'done' means for a commit.
