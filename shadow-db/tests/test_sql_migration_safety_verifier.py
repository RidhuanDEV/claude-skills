import sys
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import sql_migration_safety_verifier as verifier  # noqa: E402


class SqlMigrationSafetyVerifierTests(unittest.TestCase):
    def test_self_test_probes(self) -> None:
        res = verifier.run_self_test()
        self.assertTrue(res["all_passed"], f"Self-test failures: {res}")
        self.assertEqual(res["total_probes"], 7)

    def test_alter_column_type_blocked_outside_contract_phase(self) -> None:
        res = verifier.check_ddl("SET lock_timeout = '2s'; ALTER TABLE users ALTER COLUMN phone TYPE VARCHAR(32);")
        self.assertFalse(res["passed"])
        self.assertTrue(any("ALTER COLUMN TYPE" in e for e in res["errors"]))

    def test_raw_auth_jwt_inside_rls_rejected(self) -> None:
        res = verifier.check_rls("CREATE POLICY p ON items FOR SELECT TO authenticated USING (org_id = auth.jwt()->>'org_id');")
        self.assertFalse(res["passed"])


if __name__ == "__main__":
    unittest.main()
