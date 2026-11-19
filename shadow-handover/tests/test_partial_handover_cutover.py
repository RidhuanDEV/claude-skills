from __future__ import annotations

import hashlib
import unittest


def evaluate_handover_gate(
    *,
    release: str,
    artifacts: dict[str, str],
    walkthrough_passed: bool,
    old_shift_revoked: bool,
    new_shift_access_verified: bool,
) -> dict[str, object]:
    digests = {name: hashlib.sha256(content.encode("utf-8")).hexdigest()[:16] for name, content in artifacts.items()}
    blockers: list[str] = []
    if not walkthrough_passed:
        blockers.append("Operator walkthrough not completed.")
    if not (old_shift_revoked and new_shift_access_verified):
        blockers.append("Shift access cutover incomplete (old access not revoked or new access unverified).")
    return {
        "release": release,
        "status": "READY_FOR_BAST" if not blockers else "BLOCKED_CUTOVER",
        "artifact_digests": digests,
        "blockers": blockers,
    }


class PartialHandoverCutoverTests(unittest.TestCase):
    def test_t05_e05_release_3_2_partial_handover_enforces_walkthrough_and_shift_cutover(self) -> None:
        blocked = evaluate_handover_gate(
            release="3.2.0",
            artifacts={"runbook.md": "# Runbook v3.2", "sbom.json": '{"bomFormat":"CycloneDX"}'},
            walkthrough_passed=True,
            old_shift_revoked=False,
            new_shift_access_verified=True,
        )
        self.assertEqual(blocked["status"], "BLOCKED_CUTOVER")
        self.assertTrue(blocked["artifact_digests"]["sbom.json"])

        ready = evaluate_handover_gate(
            release="3.2.0",
            artifacts={"runbook.md": "# Runbook v3.2", "sbom.json": '{"bomFormat":"CycloneDX"}'},
            walkthrough_passed=True,
            old_shift_revoked=True,
            new_shift_access_verified=True,
        )
        self.assertEqual(ready["status"], "READY_FOR_BAST")
        self.assertEqual(ready["blockers"], [])


if __name__ == "__main__":
    unittest.main()
