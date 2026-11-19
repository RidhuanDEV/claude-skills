from __future__ import annotations

import unittest

VERSIONED_CONTROLS = {
    "ASVS-5.0-V4.1.1": "Server-side authorization and tenant ownership check on every data export.",
    "NIST-SSDF-SP800-218-PW.7": "Review and verify code for security vulnerabilities before release.",
}


def export_tenant_rows(
    caller_tenant: str,
    requested_tenant: str,
    rows: list[dict[str, str]],
) -> dict[str, object]:
    if caller_tenant != requested_tenant:
        return {
            "status": "DENIED",
            "control": "ASVS-5.0-V4.1.1",
            "rows": [],
        }
    filtered = [r for r in rows if r["tenant_id"] == caller_tenant]
    return {"status": "ALLOWED", "control": "ASVS-5.0-V4.1.1", "rows": filtered}


class SecurityTenantExportTests(unittest.TestCase):
    def test_t20_enforces_two_tenant_export_boundary_with_versioned_control_ids(self) -> None:
        dataset = [
            {"id": "1", "tenant_id": "t-alpha", "payload": "alpha-secret"},
            {"id": "2", "tenant_id": "t-beta", "payload": "beta-secret"},
        ]
        own = export_tenant_rows("t-alpha", "t-alpha", dataset)
        self.assertEqual(own["status"], "ALLOWED")
        self.assertEqual(len(own["rows"]), 1)
        self.assertEqual(own["rows"][0]["tenant_id"], "t-alpha")

        cross = export_tenant_rows("t-alpha", "t-beta", dataset)
        self.assertEqual(cross["status"], "DENIED")
        self.assertEqual(cross["rows"], [])
        self.assertIn(cross["control"], VERSIONED_CONTROLS)


if __name__ == "__main__":
    unittest.main()
