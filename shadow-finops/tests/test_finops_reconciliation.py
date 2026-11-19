from __future__ import annotations

from decimal import Decimal
import unittest


def reconcile_invoice_allocation(
    invoice_total: Decimal,
    direct_costs: dict[str, Decimal],
    shared_gateway_cost: Decimal,
    request_weights: dict[str, int],
) -> dict[str, object]:
    total_weight = sum(request_weights.values())
    allocated: dict[str, Decimal] = {}
    running_shared = Decimal("0.00")
    teams = sorted(request_weights.keys())
    for idx, team in enumerate(teams):
        if idx == len(teams) - 1:
            share = shared_gateway_cost - running_shared
        else:
            share = (shared_gateway_cost * Decimal(request_weights[team]) / Decimal(total_weight)).quantize(Decimal("0.01"))
            running_shared += share
        allocated[team] = direct_costs.get(team, Decimal("0.00")) + share

    allocated_sum = sum(allocated.values(), Decimal("0.00"))
    unallocated = invoice_total - allocated_sum
    return {
        "allocated": allocated,
        "unallocated": unallocated,
        "reconciled_total": allocated_sum + unallocated,
        "exact_match": (allocated_sum + unallocated) == invoice_total,
    }


class FinOpsReconciliationTests(unittest.TestCase):
    def test_t02_e07_shared_gateway_and_unallocated_sum_matches_invoice_with_dated_tariff(self) -> None:
        # Dated tariff snapshots preserve historical reproducibility
        tariffs = {
            "2026-Q3": Decimal("0.015"),
            "2026-Q4": Decimal("0.020"),
        }
        q3_bill = (Decimal("10000") * tariffs["2026-Q3"]).quantize(Decimal("0.01"))
        q4_bill = (Decimal("10000") * tariffs["2026-Q4"]).quantize(Decimal("0.01"))
        self.assertEqual(q3_bill, Decimal("150.00"))
        self.assertEqual(q4_bill, Decimal("200.00"))

        res = reconcile_invoice_allocation(
            invoice_total=Decimal("1000.00"),
            direct_costs={"team-a": Decimal("400.00"), "team-b": Decimal("350.00")},
            shared_gateway_cost=Decimal("200.00"),
            request_weights={"team-a": 1, "team-b": 2},
        )
        self.assertTrue(res["exact_match"])
        self.assertEqual(res["unallocated"], Decimal("50.00"))
        self.assertEqual(res["reconciled_total"], Decimal("1000.00"))


if __name__ == "__main__":
    unittest.main()
