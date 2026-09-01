from __future__ import annotations

import unittest
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from pydantic import ValidationError

from src.schema.plan import BudgetLedger, Plan, PlanItem
from src.schema.preferences import Axis, DislikeSignal

NOW = datetime(2026, 9, 1, tzinfo=UTC)


class CoreSchemaTests(unittest.TestCase):
    def test_budget_rejects_overcommit(self) -> None:
        with self.assertRaises(ValidationError):
            BudgetLedger(
                money_total_sgd=10,
                money_spent_sgd=7,
                money_committed_sgd=4,
                hours_per_week=2,
                tries_total=2,
            )

    def test_plan_total_must_equal_items(self) -> None:
        item = PlanItem(listing_id="one", session_at=NOW, cost_sgd=Decimal(5))
        with self.assertRaises(ValidationError):
            Plan(plan_id="plan", items=[item], total_cost_sgd=4, ledger_version=0)

    def test_thin_plan_names_binding_constraint(self) -> None:
        item = PlanItem(listing_id="one", session_at=NOW, cost_sgd=0)
        with self.assertRaises(ValidationError):
            Plan(plan_id="plan", items=[item], total_cost_sgd=0, ledger_version=0, thin=True)

    def test_seed_confidence_is_bounded(self) -> None:
        with self.assertRaises(ValidationError):
            Axis(value=1, confidence=0.5, provenance="seed", updated_at=NOW)

    def test_dislike_decays_below_influence_floor(self) -> None:
        dislike = DislikeSignal(
            axis="intensity",
            listing_id="one",
            attribution="activity",
            strength=1,
            recorded_at=NOW,
        )
        self.assertEqual(0, dislike.effective_strength(NOW + timedelta(days=360)))


if __name__ == "__main__":
    unittest.main()
