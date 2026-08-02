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

    def test_build_campaign_plan_uses_requested_brand_kit_and_template(
        self,
    ) -> None:
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

        for deliverable in plan["deliverables"]:
            self.assertEqual(
                deliverable["brand_kit_id"],
                request["brand_kit"]["id"],
                f"deliverable {deliverable} must use the requested brand kit",
            )
            self.assertEqual(
                deliverable["template_id"],
                request["template"]["id"],
                f"deliverable {deliverable} must use the requested template",
            )

    def test_requests_win_over_saved_account_defaults(self) -> None:
        request = json.loads(Path("fixtures/request.json").read_text())
        accounts = [
            {
                "id": "row-999",
                "company_id": "company-test",
                "company_name": "Test Co",
                "domain": "test-co.example",
                "segment": "testing",
                "saved_brand_kit_id": "brand-kit-old-default",
                "saved_template_id": "template-old-default",
            }
        ]
        plan = build_campaign_plan(
            TargetAccountTool(accounts),
            brand_kit_id=request["brand_kit"]["id"],
            template_id=request["template"]["id"],
            page_size=1,
        )

        for deliverable in plan["deliverables"]:
            self.assertEqual(
                deliverable["brand_kit_id"],
                request["brand_kit"]["id"],
                "saved brand kit defaults must not override the requested brand kit",
            )
            self.assertEqual(
                deliverable["template_id"],
                request["template"]["id"],
                "saved template defaults must not override the requested template",
            )


if __name__ == "__main__":
    unittest.main()
