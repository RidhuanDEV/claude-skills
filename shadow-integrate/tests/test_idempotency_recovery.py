from __future__ import annotations

import runpy
import unittest
from pathlib import Path

RECONCILE = runpy.run_path(
    str(Path(__file__).resolve().parents[1] / "scripts" / "reconcile_unknown.py")
)


class SyntheticPaymentLedger:
    """Simulates durable local DB + provider state across crash and empty-cache restart."""

    def __init__(self) -> None:
        self.provider_charges: dict[str, dict[str, object]] = {}
        self.local_orders: dict[str, dict[str, object]] = {}
        self.processed_webhooks: set[str] = set()
        self.business_mutations = 0
        self.ephemeral_cache: dict[str, str] = {}

    def charge_with_timeout_after_remote_commit(self, order_id: str, idempotency_key: str, amount: int) -> None:
        self.local_orders[order_id] = {
            "status": "PENDING_UNKNOWN",
            "idempotency_key": idempotency_key,
            "version": 1,
        }
        # Remote commits, then network times out before client receives 200
        if idempotency_key not in self.provider_charges:
            self.provider_charges[idempotency_key] = {
                "order_id": order_id,
                "amount": amount,
                "state": "SETTLED",
                "event_seq": 2,
            }
        raise TimeoutError("Read timed out after remote provider commit")

    def simulate_crash_and_empty_cache_restart(self) -> None:
        self.ephemeral_cache.clear()

    def apply_webhook_event(self, event_id: str, order_id: str, event_seq: int, state: str) -> str:
        if event_id in self.processed_webhooks:
            return "DUPLICATE_IGNORED"
        order = self.local_orders[order_id]
        if event_seq < int(order["version"]):
            self.processed_webhooks.add(event_id)
            return "STALE_EVENT_IGNORED"
        self.processed_webhooks.add(event_id)
        order["status"] = state
        order["version"] = event_seq
        self.business_mutations += 1
        return "APPLIED"

    def reconcile_via_provider_inquiry(self, order_id: str) -> str:
        order = self.local_orders[order_id]
        key = str(order["idempotency_key"])
        remote = self.provider_charges.get(key)
        if not remote:
            return "PROVIDER_NOT_FOUND_SAFE_RETRY"
        if order["status"] == "SETTLED":
            return "ALREADY_RECONCILED"
        order["status"] = str(remote["state"])
        order["version"] = max(int(order["version"]), int(remote["event_seq"]))
        self.business_mutations += 1
        return "RECONCILED_SINGLE_MUTATION"


class IdempotencyRecoveryTests(unittest.TestCase):
    def test_t06_e04_timeout_crash_empty_cache_stale_webhook_and_provider_reconcile(self) -> None:
        ledger = SyntheticPaymentLedger()
        with self.assertRaises(TimeoutError):
            ledger.charge_with_timeout_after_remote_commit("ord-900", "idem-900", 150000)

        ledger.simulate_crash_and_empty_cache_restart()

        # Reconcile via provider inquiry -> exactly one business mutation
        r1 = ledger.reconcile_via_provider_inquiry("ord-900")
        self.assertEqual(r1, "RECONCILED_SINGLE_MUTATION")
        self.assertEqual(ledger.business_mutations, 1)

        # Older out-of-order webhook arrives after reconciliation -> ignored
        w_old = ledger.apply_webhook_event("evt-1", "ord-900", event_seq=1, state="PENDING")
        self.assertEqual(w_old, "STALE_EVENT_IGNORED")
        self.assertEqual(ledger.local_orders["ord-900"]["status"], "SETTLED")
        self.assertEqual(ledger.business_mutations, 1)

        # Duplicate webhook replay & second inquiry do not double-mutate
        self.assertEqual(ledger.apply_webhook_event("evt-1", "ord-900", event_seq=1, state="PENDING"), "DUPLICATE_IGNORED")
        self.assertEqual(ledger.reconcile_via_provider_inquiry("ord-900"), "ALREADY_RECONCILED")
        self.assertEqual(ledger.business_mutations, 1)
        self.assertEqual(
            RECONCILE["decide"]({"operation_id": "ord-900", "state": "UNKNOWN", "inquiry_supported": True}),
            "QUERY_STATUS",
        )
        self.assertEqual(
            RECONCILE["decide"](
                {
                    "operation_id": "ord-900",
                    "state": "UNKNOWN",
                    "inquiry": {"verified": True, "operation_id": "ord-900", "state": "CONFIRMED"},
                }
            ),
            "RECORD_CONFIRMED",
        )


if __name__ == "__main__":
    unittest.main()
