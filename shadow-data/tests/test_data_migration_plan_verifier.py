import sys
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import data_migration_plan_verifier as verifier  # noqa: E402


class DataMigrationPlanVerifierTests(unittest.TestCase):
    def test_self_test_probes(self) -> None:
        res = verifier.run_self_test()
        self.assertTrue(res["all_passed"], f"Self-test failures: {res}")
        self.assertEqual(res["total_probes"], 7)

    def test_authorized_contract_phase_passes_when_telemetry_and_l4_confirmed(self) -> None:
        res = verifier.check_migration_phases(
            {
                "destructive_ddl_in_expand_phase": False,
                "mixed_version_rollback_tested": True,
                "contract_phase_requested": True,
                "zero_legacy_readers_writers_verified": True,
                "explicit_l4_destructive_approval": True,
                "ephemeral_docker_cleanup_enforced": True,
            }
        )
        self.assertTrue(res["passed"])


if __name__ == "__main__":
    unittest.main()
