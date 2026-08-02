from __future__ import annotations

import json
from pathlib import Path

from repair_lab import (
    TargetAccountTool,
    build_campaign_plan,
    evaluate_campaign_coverage,
)


def load_fixture(name: str) -> object:
    return json.loads(Path("fixtures", name).read_text())


def main() -> None:
    request = load_fixture("request.json")
    accounts = load_fixture("target_accounts.json")
    assert isinstance(request, dict)
    assert isinstance(accounts, list)

    plan = build_campaign_plan(
        TargetAccountTool(accounts),
        brand_kit_id=str(request["brand_kit"]["id"]),
        template_id=str(request["template"]["id"]),
    )
    passed, detail = evaluate_campaign_coverage(plan, accounts)
    print(json.dumps(plan, indent=2))
    print(f"EVAL {'PASS' if passed else 'FAIL'}: {detail}")


if __name__ == "__main__":
    main()
