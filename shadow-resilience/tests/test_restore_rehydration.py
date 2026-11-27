from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import ModuleType

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "drill_evidence.py"


def _load_drill_evidence() -> ModuleType:
    spec = importlib.util.spec_from_file_location("drill_evidence_restore", SCRIPT)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load {SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


drill = _load_drill_evidence()


def _receipt() -> dict[str, object]:
    """Canonical drill_receipt.json contract: RTO 1125s, RPO 288s against 1800s/900s objectives."""
    return {
        "disruption_at": "2026-11-22T01:00:00+00:00",
        "recovered_checkpoint_at": "2026-11-22T00:55:12+00:00",
        "business_verified_at": "2026-11-22T01:18:45+00:00",
        "required_dependencies_verified": True,
        "consumer_workflow_passed": True,
        "checkpoint_verified_in_source_timeline": True,
        "tombstones_replayed_count": 14,
        "rpo_objective_sec": 900,
        "rto_objective_sec": 1800,
    }


class DrillObjectiveTests(unittest.TestCase):
    def test_canonical_receipt_within_objectives_passes(self) -> None:
        self.assertEqual(
            drill.assess(_receipt()), {"rto_seconds": 1125.0, "rpo_upper_bound_seconds": 288.0, "issues": []}
        )

    def test_measurement_equal_to_objective_passes(self) -> None:
        record = {**_receipt(), "rto_objective_sec": 1125, "rpo_objective_sec": 288.0}
        self.assertEqual(drill.assess(record)["issues"], [])

    def test_rto_over_objective_fails(self) -> None:
        record = {**_receipt(), "rto_objective_sec": 1124}
        self.assertEqual(drill.assess(record)["issues"], ["RTO objective exceeded"])

    def test_rpo_over_objective_fails(self) -> None:
        record = {**_receipt(), "rpo_objective_sec": 287}
        self.assertEqual(drill.assess(record)["issues"], ["RPO objective exceeded"])

    def test_invalid_objective_values_fail(self) -> None:
        for value in ("1800", "true", True, None, -1, float("nan"), float("inf"), [1800]):
            with self.subTest(value=value):
                record = {**_receipt(), "rto_objective_sec": value}
                self.assertEqual(drill.assess(record)["issues"], ["Invalid RTO objective"])

    def test_missing_objectives_skip_comparison(self) -> None:
        record = _receipt()
        del record["rto_objective_sec"], record["rpo_objective_sec"]
        self.assertEqual(drill.assess(record)["issues"], [])


class DrillEvidenceGateTests(unittest.TestCase):
    def test_string_flags_do_not_verify_recovery(self) -> None:
        for key in ("required_dependencies_verified", "consumer_workflow_passed"):
            for value in ("true", "True", 1, None):
                with self.subTest(key=key, value=value):
                    result = drill.assess({**_receipt(), key: value})
                    self.assertIsNone(result["rto_seconds"])
                    self.assertIn("Business recovery unverified", result["issues"])
        result = drill.assess({**_receipt(), "checkpoint_verified_in_source_timeline": "true"})
        self.assertIsNone(result["rpo_upper_bound_seconds"])
        self.assertIn("Recovery point unverified", result["issues"])

    def test_missing_keys_and_empty_record_fail(self) -> None:
        self.assertEqual(drill.assess({})["issues"], ["Missing or invalid disruption timestamp"])
        record = _receipt()
        del record["business_verified_at"]
        self.assertIn("Business recovery unverified", drill.assess(record)["issues"])

    def test_wrong_type_or_naive_timestamps_fail(self) -> None:
        for value in (1763773200, "2026-11-22T01:00:00", "not-a-date"):
            with self.subTest(value=value):
                result = drill.assess({**_receipt(), "disruption_at": value})
                self.assertIn("Missing or invalid disruption timestamp", result["issues"])
                self.assertIsNone(result["rto_seconds"])

    def test_verification_before_disruption_fails(self) -> None:
        result = drill.assess({**_receipt(), "business_verified_at": "2026-11-22T00:59:59+00:00"})
        self.assertIsNone(result["rto_seconds"])
        self.assertIn("Business recovery unverified", result["issues"])


class DrillEvidenceCliTests(unittest.TestCase):
    def _run(self, record: object) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "drill_receipt.json"
            path.write_text(json.dumps(record), encoding="utf-8")
            return subprocess.run(
                [sys.executable, "-B", str(SCRIPT), str(path)], capture_output=True, text=True, timeout=60, check=False
            )

    def test_cli_exit_codes(self) -> None:
        ok = self._run(_receipt())
        self.assertEqual(ok.returncode, 0, ok.stdout + ok.stderr)
        self.assertEqual(json.loads(ok.stdout)["issues"], [])
        over = self._run({**_receipt(), "rto_objective_sec": 60})
        self.assertEqual(over.returncode, 1)
        self.assertIn("RTO objective exceeded", json.loads(over.stdout)["issues"])
        self.assertEqual(self._run([_receipt()]).returncode, 2)


if __name__ == "__main__":
    unittest.main()
