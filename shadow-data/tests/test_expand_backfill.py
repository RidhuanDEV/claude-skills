"""Expand-backfill hazards on SQLite, each tied to the shipped verifier gate that must catch it."""
from __future__ import annotations

import importlib.util
import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import ModuleType
from typing import Any

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "data_migration_plan_verifier.py"


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("data_migration_plan_verifier_under_test", SCRIPT)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


verifier = _load()


def safe_plan(**overrides: Any) -> dict[str, Any]:
    plan: dict[str, Any] = {
        "pagination_mode": "keyset",
        "batch_size": 1000,
        "pause_ms": 50,
        "replica_lag_throttle_enabled": True,
        "resumable_checkpoint_persisted": True,
        "handles_concurrent_legacy_writers": True,
        "reconciliation_check_included": True,
        "lock_timeout_set": True,
    }
    plan.update(overrides)
    return plan


def safe_phases(**overrides: Any) -> dict[str, Any]:
    phases: dict[str, Any] = {
        "destructive_ddl_in_expand_phase": False,
        "mixed_version_rollback_tested": True,
        "contract_phase_requested": False,
        "ephemeral_docker_cleanup_enforced": True,
    }
    phases.update(overrides)
    return phases


def safe_seed(**overrides: Any) -> dict[str, Any]:
    seed: dict[str, Any] = {
        "uses_upsert_idempotency": True,
        "demo_seed_blocked_in_production": True,
        "separates_system_vs_demo_seeds": True,
    }
    seed.update(overrides)
    return seed


class ExpandBackfillScenario(unittest.TestCase):
    """The SQLite scenario proves the hazard; the shipped gate must reject a plan that ignores it."""

    def setUp(self) -> None:
        self.db = sqlite3.connect(":memory:")
        self.addCleanup(self.db.close)
        self.db.executescript("""
            CREATE TABLE orders(id INTEGER PRIMARY KEY, cents INTEGER NOT NULL);
            INSERT INTO orders VALUES (1, 10), (2, 20), (3, 30);
            ALTER TABLE orders ADD COLUMN minor_units INTEGER;
            CREATE TABLE checkpoint(last_id INTEGER NOT NULL);
            INSERT INTO checkpoint VALUES (0);
        """)

    def batch(self, interrupt: bool = False) -> int:
        with self.db:
            (pos,) = self.db.execute("SELECT last_id FROM checkpoint").fetchone()
            ids = self.db.execute("SELECT id FROM orders WHERE id>? ORDER BY id LIMIT 2", (pos,)).fetchall()
            for key in ids:
                self.db.execute("UPDATE orders SET minor_units=cents WHERE id=?", key)
            if interrupt:
                raise RuntimeError("worker lost")
            if ids:
                self.db.execute("UPDATE checkpoint SET last_id=?", ids[-1])
        return len(ids)

    def mismatch(self) -> list[tuple[int]]:
        return self.db.execute("SELECT id FROM orders WHERE minor_units IS NOT cents ORDER BY id").fetchall()

    def test_interrupted_batch_is_replayable_and_gate_requires_checkpoint(self) -> None:
        with self.assertRaises(RuntimeError):
            self.batch(interrupt=True)
        self.assertEqual(self.mismatch(), [(1,), (2,), (3,)])
        self.assertEqual([self.batch(), self.batch(), self.batch()], [2, 1, 0])
        self.assertEqual(self.mismatch(), [])
        self.assertTrue(verifier.check_backfill_plan(safe_plan())["passed"])
        res = verifier.check_backfill_plan(safe_plan(resumable_checkpoint_persisted=False))
        self.assertFalse(res["passed"])
        self.assertTrue(any("checkpoint" in e for e in res["errors"]))

    def test_high_water_mark_misses_legacy_writer_and_gate_requires_parity(self) -> None:
        self.batch()
        self.db.execute("UPDATE orders SET cents=12 WHERE id=1")
        self.batch()
        self.assertEqual(self.batch(), 0)
        self.assertEqual(self.mismatch(), [(1,)])
        for flag in ("handles_concurrent_legacy_writers", "reconciliation_check_included"):
            res = verifier.check_backfill_plan(safe_plan(**{flag: False}))
            self.assertFalse(res["passed"], flag)
        # Install a compatibility writer before reconciliation and the read switch.
        self.db.executescript("""
            CREATE TRIGGER sync_old_writer AFTER UPDATE OF cents ON orders
            BEGIN UPDATE orders SET minor_units=NEW.cents WHERE id=NEW.id; END;
            UPDATE orders SET minor_units=cents WHERE minor_units IS NOT cents;
            UPDATE orders SET cents=13 WHERE id=1;
        """)
        self.assertEqual(self.mismatch(), [])


class BackfillPlanGate(unittest.TestCase):
    def test_safe_plan_passes(self) -> None:
        res = verifier.check_backfill_plan(safe_plan())
        self.assertTrue(res["passed"], res)
        self.assertEqual(res["errors"], [])

    def test_batch_bounds_are_inclusive_and_outside_fails(self) -> None:
        self.assertTrue(verifier.check_backfill_plan(safe_plan(batch_size=100))["passed"])
        self.assertTrue(verifier.check_backfill_plan(safe_plan(batch_size=10000))["passed"])
        self.assertFalse(verifier.check_backfill_plan(safe_plan(batch_size=99))["passed"])
        self.assertFalse(verifier.check_backfill_plan(safe_plan(batch_size=10001))["passed"])

    def test_offset_pagination_fails(self) -> None:
        self.assertFalse(verifier.check_backfill_plan(safe_plan(pagination_mode="offset"))["passed"])

    def test_string_flags_fail(self) -> None:
        for flag in ("resumable_checkpoint_persisted", "handles_concurrent_legacy_writers", "reconciliation_check_included"):
            for value in ("true", "True", 1):
                with self.subTest(flag=flag, value=value):
                    self.assertFalse(verifier.check_backfill_plan(safe_plan(**{flag: value}))["passed"])

    def test_wrong_numeric_types_fail_instead_of_crashing(self) -> None:
        for value in ("1000", None, True, 1000.5, "abc"):
            with self.subTest(batch_size=value):
                self.assertFalse(verifier.check_backfill_plan(safe_plan(batch_size=value))["passed"])
        res = verifier.check_backfill_plan(safe_plan(pause_ms="75", replica_lag_throttle_enabled="true"))
        self.assertFalse(res["passed"])

    def test_no_throttle_fails(self) -> None:
        self.assertFalse(verifier.check_backfill_plan(safe_plan(pause_ms=0, replica_lag_throttle_enabled=False))["passed"])
        self.assertTrue(verifier.check_backfill_plan(safe_plan(pause_ms=0, replica_lag_throttle_enabled=True))["passed"])

    def test_empty_plan_fails(self) -> None:
        res = verifier.check_backfill_plan({})
        self.assertFalse(res["passed"])
        self.assertGreaterEqual(len(res["errors"]), 6)


class MigrationPhaseGate(unittest.TestCase):
    def test_additive_expand_passes(self) -> None:
        self.assertTrue(verifier.check_migration_phases(safe_phases())["passed"])

    def test_destructive_expand_fails_including_string_flag(self) -> None:
        for value in (True, "true", "false", None):
            with self.subTest(value=value):
                self.assertFalse(verifier.check_migration_phases(safe_phases(destructive_ddl_in_expand_phase=value))["passed"])

    def test_contract_phase_string_flag_still_held(self) -> None:
        for value in (True, "true", "false"):
            with self.subTest(value=value):
                res = verifier.check_migration_phases(safe_phases(contract_phase_requested=value))
                self.assertFalse(res["passed"])
                self.assertTrue(all("CONTRACT_HOLD" in e for e in res["errors"]))

    def test_contract_phase_with_string_approvals_held(self) -> None:
        res = verifier.check_migration_phases(
            safe_phases(contract_phase_requested=True, zero_legacy_readers_writers_verified="true",
                        explicit_l4_destructive_approval="true")
        )
        self.assertFalse(res["passed"])
        self.assertEqual(len(res["errors"]), 2)

    def test_docker_cleanup_string_false_fails(self) -> None:
        for value in (False, "false", "true", None):
            with self.subTest(value=value):
                self.assertFalse(verifier.check_migration_phases(safe_phases(ephemeral_docker_cleanup_enforced=value))["passed"])

    def test_empty_phases_fail(self) -> None:
        self.assertFalse(verifier.check_migration_phases({})["passed"])


class SeedSafetyGate(unittest.TestCase):
    def test_safe_seed_passes(self) -> None:
        self.assertTrue(verifier.check_seed_safety(safe_seed())["passed"])

    def test_string_flags_fail(self) -> None:
        for flag in ("uses_upsert_idempotency", "demo_seed_blocked_in_production", "separates_system_vs_demo_seeds"):
            with self.subTest(flag=flag):
                self.assertFalse(verifier.check_seed_safety(safe_seed(**{flag: "true"}))["passed"])

    def test_missing_keys_and_empty_fail(self) -> None:
        self.assertEqual(len(verifier.check_seed_safety({})["errors"]), 3)
        seed = safe_seed()
        del seed["demo_seed_blocked_in_production"]
        self.assertFalse(verifier.check_seed_safety(seed)["passed"])


class VerifierCli(unittest.TestCase):
    def run_cli(self, flag: str, payload: object) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "input.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            return subprocess.run([sys.executable, "-B", str(SCRIPT), flag, str(path)],
                                  capture_output=True, text=True, timeout=30)

    def test_cli_exit_codes(self) -> None:
        self.assertEqual(self.run_cli("--check-backfill-plan", safe_plan()).returncode, 0)
        self.assertEqual(self.run_cli("--check-backfill-plan", safe_plan(pagination_mode="offset")).returncode, 1)
        self.assertEqual(self.run_cli("--check-migration-phases", safe_phases(contract_phase_requested="true")).returncode, 1)
        self.assertEqual(self.run_cli("--check-seed-safety", {}).returncode, 1)

    def test_cli_rejects_non_object_json(self) -> None:
        self.assertNotEqual(self.run_cli("--check-seed-safety", []).returncode, 0)


if __name__ == "__main__":
    unittest.main()
