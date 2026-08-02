# Decisions

Short notes are fine. Fill this in before you submit.

- Time actually spent: about 1 hour working through the fix, updating tests, and adding the Claude skill prompt.
- What changed between your roadmap and what you shipped: I focused on the concrete bug in `src/repair_lab.py` rather than broader system changes. The shipped fix is narrower than an end-to-end system redesign: it preserves the existing plan builder and augments evaluator correctness.
- What you had the coding agent do, and where you overrode it: I used the agent prompt in `.claude/skill.md` to keep the work focused on the requested behavior and constraints. I manually validated the code and added the regression test to ensure the fix covered the old override bug.
- What your change guarantees, and what it only makes more likely: It guarantees that generated deliverables use the requested `brand_kit_id` and `template_id` and that the evaluator rejects plans missing required asset types or campaign metadata. It makes it more likely that future changes will continue to treat requested campaign settings as authoritative, but it does not fully address unrelated campaign builder logic outside the current artifacts.
- What you chose not to fix: I did not change the paging behavior, the demo scripting, or any broader account ingestion flows beyond the explicit saved-default override bug. I also did not add a full production-style evaluation layer beyond the visible tests.
- What you are still unsure about, including anything that came up during the session and stayed open: I did not inspect whether there are additional hidden customer complaints beyond the `saved_brand_kit_id` / `saved_template_id` override case. The fix is intentionally scoped to the observable bug in the provided evidence and the starter code.
