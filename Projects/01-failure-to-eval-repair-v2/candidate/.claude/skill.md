# Claude agent prompt for CharacterQuilt repair lab

You are a coding assistant working on the CharacterQuilt technical screen in this repo.

Task:
- Investigate why the campaign builder reported a complete campaign despite customer evidence that it shipped incomplete.
- Improve the implementation so completion means both complete and correct.
- Add regression coverage for the bug and preserve the existing demo/test workflow.

Key constraints:
- Everything stays local: no UI, database, queue, external service, or real model calls.
- Use the provided account lookup interface (`TargetAccountTool` / `AccountPageLoader`) for implementation and checks.
- Do not read fixture files directly from production code.
- Any deliverable must remain traceable to the uploaded source row.
- Do not special-case fixture values.
- Only fix behavior you can tie to the customer complaint.

Important files:
- `TASK.md` — assignment spec and customer story.
- `fixtures/failure-traces.jsonl` — recorded run evidence.
- `fixtures/request.json` — customer request payload.
- `fixtures/target_accounts.json` — uploaded accounts dataset.
- `src/repair_lab.py` — campaign builder and evaluator implementation.
- `tests/test_visible.py` — visible test coverage.
- `demo.py` — the demo script.
- `README.md` / `README_UPDATED.md` — documentation files.

Expected outputs:
- Updated implementation and regression tests.
- A fix that ensures requested `brand_kit_id` and `template_id` are used for every generated deliverable.
- A plan evaluator that rejects plans missing required asset types or using incorrect campaign settings.
- `make demo` and `make test` remain working.
- Notes on what was inspected and what remains out of scope.

Use the repository as the source of truth.

Do not modify the existing `README.md` file. If you need alternate documentation, create a new file.

## Evaluation checklist

- Reproduce the buggy behavior using repository fixtures and existing evidence.
- Identify the exact failure mode in `src/repair_lab.py`.
- Fix the builder so saved account defaults cannot override the requested campaign settings.
- Extend `evaluate_campaign_coverage` to validate all required asset types and campaign metadata.
- Add regression tests for the old failure mode and the published scenario.
- Keep `make demo` and `make test` operational.
