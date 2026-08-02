from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


REQUIRED_ASSET_TYPES = (
    "landing_page",
    "linkedin_ad_1",
    "linkedin_ad_2",
    "linkedin_ad_3",
)


@dataclass(frozen=True)
class ToolPage:
    rows: list[dict[str, Any]]
    next_cursor: str | None
    truncated: bool


class AccountPageLoader(Protocol):
    def load_page(
        self,
        *,
        cursor: str | None = None,
        page_size: int = 2,
    ) -> ToolPage: ...


class TargetAccountTool:
    """Deterministic stand-in for a paginated uploaded-account tool."""

    def __init__(self, accounts: list[dict[str, Any]]) -> None:
        self._accounts = [dict(account) for account in accounts]

    def load_page(
        self,
        *,
        cursor: str | None = None,
        page_size: int = 2,
    ) -> ToolPage:
        start = int(cursor or "0")
        rows = self._accounts[start : start + page_size]
        next_index = start + len(rows)
        next_cursor = (
            str(next_index)
            if next_index < len(self._accounts)
            else None
        )
        return ToolPage(
            rows=rows,
            next_cursor=next_cursor,
            truncated=next_cursor is not None,
        )


def _make_deliverables(
    accounts: list[dict[str, Any]],
    *,
    brand_kit_id: str,
    template_id: str,
) -> list[dict[str, str]]:
    deliverables: list[dict[str, str]] = []
    for account in accounts:
        for asset_type in REQUIRED_ASSET_TYPES:
            deliverables.append(
                {
                    "source_row_id": str(account["id"]),
                    "company_id": str(account["company_id"]),
                    "company_name": str(account["company_name"]),
                    "asset_type": asset_type,
                    "brand_kit_id": brand_kit_id,
                    "template_id": template_id,
                }
            )
    return deliverables


def build_campaign_plan(
    tool: AccountPageLoader,
    *,
    brand_kit_id: str,
    template_id: str,
    page_size: int = 2,
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    cursor: str | None = None
    while True:
        page = tool.load_page(cursor=cursor, page_size=page_size)
        rows.extend(page.rows)
        if not page.truncated:
            break
        cursor = page.next_cursor

    return {
        "source_row_ids": [str(row["id"]) for row in rows],
        "deliverables": _make_deliverables(
            rows,
            brand_kit_id=brand_kit_id,
            template_id=template_id,
        ),
        "brand_kit_id": brand_kit_id,
        "template_id": template_id,
        "complete": True,
    }


def evaluate_campaign_coverage(
    plan: dict[str, Any],
    accounts: list[dict[str, Any]],
) -> tuple[bool, str]:
    """The currently deployed evaluator; the customer disputes its result."""
    expected_rows = {str(account["id"]) for account in accounts}
    observed_rows = {
        str(value) for value in plan.get("source_row_ids", [])
    }
    missing_rows = sorted(expected_rows - observed_rows)
    if missing_rows:
        return False, f"campaign omitted source rows: {', '.join(missing_rows)}"

    deliverables = plan.get("deliverables", [])
    for row_id in sorted(expected_rows):
        observed_types = {
            str(item.get("asset_type"))
            for item in deliverables
            if str(item.get("source_row_id")) == row_id
        }
        if observed_types != set(REQUIRED_ASSET_TYPES):
            return False, f"source row {row_id} has the wrong asset set"

    expected_brand_kit = plan.get("brand_kit_id")
    expected_template = plan.get("template_id")
    if expected_brand_kit is None or expected_template is None:
        return False, "campaign did not declare requested campaign settings"

    for item in deliverables:
        if str(item.get("brand_kit_id")) != str(expected_brand_kit):
            return False, (
                "campaign deliverable used the wrong brand kit: "
                f"expected {expected_brand_kit}, got {item.get('brand_kit_id')}"
            )
        if str(item.get("template_id")) != str(expected_template):
            return False, (
                "campaign deliverable used the wrong template: "
                f"expected {expected_template}, got {item.get('template_id')}"
            )

    if plan.get("complete") is not True:
        return False, "campaign did not declare completion"
    return True, "every source row has the requested asset types"
