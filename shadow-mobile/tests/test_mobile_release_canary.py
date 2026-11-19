from __future__ import annotations

import unittest


def validate_mobile_release_manifest(manifest: dict[str, object]) -> list[str]:
    errors: list[str] = []
    if manifest.get("build_type") == "release":
        if manifest.get("debuggable") is True:
            errors.append("Release build must not have android:debuggable=true.")
        if manifest.get("usesCleartextTraffic") is True:
            errors.append("Release build must not allow cleartext HTTP traffic.")
        if not manifest.get("privacy_manifest_present"):
            errors.append("Missing iOS PrivacyInfo.xcprivacy manifest.")
    return errors


def evaluate_canary_cohorts(cohorts: list[dict[str, object]], max_crash_rate: float = 0.01) -> dict[str, object]:
    regressed = [c["os_cohort"] for c in cohorts if float(c["crash_rate"]) > max_crash_rate]
    return {
        "decision": "HALT_ROLLOUT" if regressed else "PROMOTE",
        "regressed_cohorts": regressed,
    }


class MobileReleaseCanaryTests(unittest.TestCase):
    def test_t08_e06_blocks_debug_flags_in_release_and_catches_older_os_canary_regression(self) -> None:
        bad_release = validate_mobile_release_manifest(
            {"build_type": "release", "debuggable": True, "usesCleartextTraffic": True, "privacy_manifest_present": False}
        )
        self.assertEqual(len(bad_release), 3)

        debug_ok = validate_mobile_release_manifest(
            {"build_type": "debug", "debuggable": True, "usesCleartextTraffic": True, "privacy_manifest_present": False}
        )
        self.assertEqual(debug_ok, [])

        # Global crash rate looks low (<0.5%), but older OS cohort regresses to 4.2% -> must halt!
        canary = evaluate_canary_cohorts(
            [
                {"os_cohort": "android-15", "crash_rate": 0.001},
                {"os_cohort": "android-14", "crash_rate": 0.002},
                {"os_cohort": "android-10-legacy", "crash_rate": 0.042},
            ]
        )
        self.assertEqual(canary["decision"], "HALT_ROLLOUT")
        self.assertEqual(canary["regressed_cohorts"], ["android-10-legacy"])


if __name__ == "__main__":
    unittest.main()
