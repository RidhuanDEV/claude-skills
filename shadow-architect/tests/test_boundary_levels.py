from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "topology_decision.py"
_spec = importlib.util.spec_from_file_location("topology_decision", SCRIPT)
assert _spec is not None and _spec.loader is not None
topology_decision = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(topology_decision)


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-B", str(SCRIPT), *args], capture_output=True, text=True, timeout=60, check=False,
    )

BASE = {"team_count": 2, "independent_scaling_proven": False, "shared_acid_transactions": True,
        "regulatory_isolation_required": False}


class ArchitectureBoundaryTests(unittest.TestCase):
    def test_c05_prefers_modular_monolith_before_split_deployment(self) -> None:
        small = topology_decision.recommend(BASE)
        self.assertEqual(small["topology"], "modular_monolith")
        self.assertIn("microservices", small["rejected"])
        regulated = topology_decision.recommend({**BASE, "team_count": 6, "independent_scaling_proven": True,
                                                 "shared_acid_transactions": False, "regulatory_isolation_required": True})
        self.assertEqual(regulated["topology"], "bounded_split_services")

    def test_shared_acid_keeps_one_store_with_workers(self) -> None:
        self.assertEqual(topology_decision.recommend({**BASE, "team_count": 6})["topology"], "modular_monolith_with_worker")
        self.assertEqual(topology_decision.recommend({**BASE, "independent_scaling_proven": True})["topology"],
                         "modular_monolith_with_worker")

    def test_unproven_or_malformed_drivers_are_rejected(self) -> None:
        for drivers in (
            {**BASE, "independent_scaling_proven": "true"},
            {**BASE, "regulatory_isolation_required": "yes"},
            {**BASE, "team_count": 0},
            {**BASE, "team_count": True},
            {key: value for key, value in BASE.items() if key != "shared_acid_transactions"},
            [],
        ):
            with self.subTest(drivers=drivers):
                self.assertEqual(topology_decision.recommend(drivers)["status"], "INVALID_INPUT")

    def test_cli_self_test(self) -> None:
        self.assertEqual(run_cli("--self-test").returncode, 0)


if __name__ == "__main__":
    unittest.main()
