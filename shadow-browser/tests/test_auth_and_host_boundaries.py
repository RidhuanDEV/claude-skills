from __future__ import annotations

import unittest
from urllib.parse import urlparse

ALLOWED_LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}


def check_browser_target_policy(url: str, approved_external_hosts: set[str] | None = None) -> dict[str, object]:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    approved = {h.lower() for h in (approved_external_hosts or set())}
    if host in ALLOWED_LOCAL_HOSTS:
        return {"allowed": True, "scope": "local"}
    if host in approved:
        return {"allowed": True, "scope": "approved_external"}
    return {
        "allowed": False,
        "scope": "external_unapproved",
        "reason": f"Host `{host}` is outside local/approved browser test boundary.",
    }


def handle_browser_session_response(status_code: int, retried: bool) -> str:
    if status_code == 401 and not retried:
        return "REAUTHENTICATE_AND_RETRY_ONCE"
    if status_code == 401 and retried:
        return "STOP_AUTH_FAILURE"
    if 200 <= status_code < 300:
        return "CONTINUE"
    return "REPORT_HTTP_ERROR"


class BrowserBoundaryTests(unittest.TestCase):
    def test_c08_detects_unapproved_external_hosts_and_recovers_401_once(self) -> None:
        self.assertTrue(check_browser_target_policy("http://127.0.0.1:5173/login")["allowed"])
        ext = check_browser_target_policy("https://prod.example.com/admin")
        self.assertFalse(ext["allowed"])
        self.assertEqual(ext["scope"], "external_unapproved")

        self.assertEqual(handle_browser_session_response(401, retried=False), "REAUTHENTICATE_AND_RETRY_ONCE")
        self.assertEqual(handle_browser_session_response(401, retried=True), "STOP_AUTH_FAILURE")
        self.assertEqual(handle_browser_session_response(200, retried=True), "CONTINUE")


if __name__ == "__main__":
    unittest.main()
