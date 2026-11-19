from __future__ import annotations

import unittest


def evaluate_rollback_safety(
    *,
    current_version: str,
    target_version: str,
    feature_flag_available: bool,
    migration_is_expand_only: bool,
) -> dict[str, object]:
    if feature_flag_available and migration_is_expand_only:
        return {"rollback_allowed": True, "mode": "FLAG_OFF_AND_BINARY_ROLLBACK"}
    if not migration_is_expand_only:
        return {
            "rollback_allowed": False,
            "mode": "BLOCKED_INCOMPATIBLE_SCHEMA",
            "reason": f"Migration between {target_version} and {current_version} dropped/altered columns incompatibly; requires forward-fix or backup restore.",
        }
    return {"rollback_allowed": True, "mode": "EXPAND_COMPATIBLE_2_VERSION_ROLLBACK"}


class IncidentAndReleaseRollbackTests(unittest.TestCase):
    def test_t07_t17_distinguishes_flag_off_and_expand_compatible_rollback_from_destructive_schema(self) -> None:
        safe_flag = evaluate_rollback_safety(
            current_version="2.4.0",
            target_version="2.3.0",
            feature_flag_available=True,
            migration_is_expand_only=True,
        )
        self.assertTrue(safe_flag["rollback_allowed"])
        self.assertEqual(safe_flag["mode"], "FLAG_OFF_AND_BINARY_ROLLBACK")

        blocked = evaluate_rollback_safety(
            current_version="2.4.0",
            target_version="2.3.0",
            feature_flag_available=True,
            migration_is_expand_only=False,
        )
        self.assertFalse(blocked["rollback_allowed"])
        self.assertEqual(blocked["mode"], "BLOCKED_INCOMPATIBLE_SCHEMA")

        expand_ok = evaluate_rollback_safety(
            current_version="2.4.0",
            target_version="2.3.0",
            feature_flag_available=False,
            migration_is_expand_only=True,
        )
        self.assertTrue(expand_ok["rollback_allowed"])
        self.assertEqual(expand_ok["mode"], "EXPAND_COMPATIBLE_2_VERSION_ROLLBACK")


if __name__ == "__main__":
    unittest.main()
