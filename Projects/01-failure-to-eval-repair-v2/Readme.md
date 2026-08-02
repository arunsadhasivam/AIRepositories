# CharacterQuilt Repair Lab

This repo is a local stand-in for a campaign builder that loads uploaded target accounts from a paginated tool, generates campaign deliverables, and evaluates whether the generated campaign is complete.

## What was wrong

The starter implementation reported a campaign complete when:
- every uploaded row had the required asset types,
- but the evaluation did not verify whether those assets were actually built with the requested campaign `brand_kit_id` and `template_id`.

That meant a plan could pass the supplied check even if one row was built with stale per-account defaults instead of the customer-selected kit/template.

## What I fixed

- `src/repair_lab.py`
  - strengthened the completeness evaluator so it checks:
    - every uploaded source row is included,
    - each row has all required asset types,
    - every deliverable uses the requested `brand_kit_id` and `template_id`.
  - removed the incorrect fallback behavior where an account’s saved kit/template could silently override the request.

- `tests/test_visible.py`
  - added coverage for:
    - the published fixed campaign plan,
    - a case where a saved account override would previously hide a bad plan,
    - the new requested-kit/template validation logic.

## Why this fix matters

- It ties every output back to the uploaded input row.
- It makes “complete” mean complete and correct, not just complete in count.
- It prevents stale per-account configuration from bypassing the customer’s selected campaign settings.

## How to run

```bash
cd candidate
make demo
make test
