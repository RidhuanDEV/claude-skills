import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import release_readiness_verifier as rrv


class ReleaseReadinessVerifierTests(unittest.TestCase):
    def test_self_test_probes(self) -> None:
        report = rrv.run_self_test()
        self.assertTrue(report["all_passed"], report)
        self.assertEqual(report["total_probes"], 7)

    def test_major_bump_with_breaking_changes_passes(self) -> None:
        violations = rrv.check_release_manifest({
            "version": "2.0.0",
            "previous_version": "1.9.4",
            "has_breaking_changes": True,
            "artifact_ref": "ghcr.io/org/api@sha256:111aaa",
            "rollback_ref": "ghcr.io/org/api@sha256:000bbb",
            "gates": {
                "quality_and_tests_passed": True,
                "security_audit_passed": True,
                "staging_uat_passed": True,
                "backup_or_recovery_point_verified": True,
                "env_parity_verified": True,
                "rollback_command_tested": True,
                "sbom_and_provenance_verified": True,
            },
        })
        self.assertEqual(violations, [])


if __name__ == "__main__":
    unittest.main()
