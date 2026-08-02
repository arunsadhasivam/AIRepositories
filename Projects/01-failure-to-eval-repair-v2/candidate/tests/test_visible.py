from __future__ import annotations

import json
import unittest
from pathlib import Path

from repair_lab import (
    TargetAccountTool,
    build_campaign_plan,
    evaluate_campaign_coverage,
)


class SuppliedEvaluatorSmokeTest(unittest.TestCase):
    def test_supplied_evaluator_accepts_the_published_plan(self) -> None:
        request = json.loads(Path("fixtures/request.json").read_text())
        accounts = json.loads(
            Path("fixtures/target_accounts.json").read_text()
        )
        plan = build_campaign_plan(
            TargetAccountTool(accounts),
            brand_kit_id=request["brand_kit"]["id"],
            template_id=request["template"]["id"],
            page_size=2,
        )
        passed, detail = evaluate_campaign_coverage(plan, accounts)
        self.assertTrue(passed, detail)


if __name__ == "__main__":
    unittest.main()
