# CharacterQuilt technical screen: repair an incomplete campaign

Read [TASK.md](TASK.md) — it has the whole assignment and the customer story.

## Summary

This repo models a campaign builder that loads uploaded target accounts through a paginated lookup tool, generates deliverables for each account, and evaluates whether the resulting campaign is complete.

The starter implementation passed the visible check shipped with the repo, but the customer evidence indicates a campaign could still be reported complete even when one account used stale per-account defaults instead of the requested campaign `brand_kit_id` and `template_id`.

## What was fixed

- Strengthened `src/repair_lab.py` so the evaluator now requires:
  - every uploaded source row appears in the campaign plan,
  - each source row includes all required asset types,
  - every deliverable uses the requested `brand_kit_id` and `template_id`.
- Removed the silent fallback where an account’s saved kit or template could override the requested campaign configuration.
- Added test coverage for incomplete campaigns that otherwise looked valid by count.

## Why this matters

A green `make demo` / `make test` run on the starter code is not sufficient evidence alone. The bug is a logical mismatch between “reported complete” and “built correctly with the customer-selected campaign settings.” This fix makes completion mean complete and correct.

## How to run

```bash
cd candidate
make demo
make test
```

## Expected packet contents

- repository with git history
- raw agent transcript, including dead ends
- `ROADMAP.md` committed before code/test edits
- updated implementation and checks
- `make demo` and `make test` output
- `DECISIONS.md` and `SUBMISSION.md` with actual time spent

## Files

- `TASK.md` — the assignment.
- `fixtures/request.json` — the customer's request.
- `fixtures/target_accounts.json` — the uploaded account list.
- `fixtures/customer_report.txt` — the customer’s note to support.
- `fixtures/failure-traces.jsonl` — the recorded run trace.
- `src/repair_lab.py` — campaign plan builder and evaluator.
- `tests/test_visible.py` — visible test coverage.
- `demo.py` — script the demo command runs.
- `DECISIONS.md`, `SUBMISSION.md` — packet documentation.
