from __future__ import annotations

import hashlib
import hmac
import json
import threading
import unittest
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any

SIGNING_KEY = b"ephemeral-test-key-never-logged"
VALID_SESSIONS: dict[str, dict[str, str]] = {
    "tok-alice": {"sub": "alice", "role": "viewer", "tenant": "tenant-a"},
    "tok-bob": {"sub": "bob", "role": "admin", "tenant": "tenant-b"},
}
TENANT_RECORDS: dict[str, list[dict[str, str]]] = {
    "tenant-a": [{"id": "rec-a1", "owner": "tenant-a", "title": "Invoice A1"}],
    "tenant-b": [{"id": "rec-b1", "owner": "tenant-b", "title": "Invoice B1"}],
}


def redact_headers(headers: dict[str, str]) -> dict[str, str]:
    redacted: dict[str, str] = {}
    for k, v in headers.items():
        if k.lower() in {"authorization", "cookie", "x-api-key"}:
            redacted[k] = "[REDACTED]"
        else:
            redacted[k] = v
    return redacted


class AuthPolicyHandler(BaseHTTPRequestHandler):
    audit_log: list[dict[str, Any]] = []

    def log_message(self, format: str, *args: object) -> None:
        return

    def _send(self, code: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        auth = self.headers.get("Authorization", "")
        token = auth.removeprefix("Bearer ").strip() if auth.startswith("Bearer ") else ""
        # Server derives identity strictly from verified token, ignoring client X-Role / X-Username headers
        claims = VALID_SESSIONS.get(token)
        self.audit_log.append(
            {
                "path": self.path,
                "headers": redact_headers(dict(self.headers.items())),
                "subject": claims["sub"] if claims else None,
            }
        )
        if not claims:
            self._send(401, {"error": "unauthorized"})
            return

        if self.path.startswith("/tenants/"):
            target_tenant = self.path.split("/tenants/", 1)[1].split("/", 1)[0]
            if target_tenant != claims["tenant"]:
                self._send(403, {"error": "cross_tenant_denied"})
                return
            if self.path.endswith("/admin-export") and claims["role"] != "admin":
                self._send(403, {"error": "insufficient_role"})
                return
            sig = hmac.new(SIGNING_KEY, target_tenant.encode("utf-8"), hashlib.sha256).hexdigest()[:12]
            self._send(200, {"records": TENANT_RECORDS[target_tenant], "attestation": sig})
            return

        self._send(404, {"error": "not_found"})


class AuthPolicyMatrixTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        AuthPolicyHandler.audit_log = []
        cls.server = HTTPServer(("127.0.0.1", 0), AuthPolicyHandler)
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.server.server_close()

    def _get(self, path: str, headers: dict[str, str] | None = None) -> tuple[int, dict[str, Any]]:
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}{path}", headers=headers or {})
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                return resp.status, json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as err:
            return err.code, json.loads(err.read().decode("utf-8"))

    def test_c06_server_enforces_rbac_tenant_isolation_and_ignores_spoofed_client_claims(self) -> None:
        code_unauth, _ = self._get("/tenants/tenant-a/records", {"X-Username": "bob", "X-Role": "admin"})
        self.assertEqual(code_unauth, 401)

        code_own, body_own = self._get("/tenants/tenant-a/records", {"Authorization": "Bearer tok-alice"})
        self.assertEqual(code_own, 200)
        self.assertEqual(body_own["records"][0]["id"], "rec-a1")

        # Spoofed client headers cannot escalate viewer -> admin or jump tenants
        code_escalate, _ = self._get(
            "/tenants/tenant-a/admin-export",
            {"Authorization": "Bearer tok-alice", "X-Role": "admin", "X-Username": "bob"},
        )
        self.assertEqual(code_escalate, 403)

        code_cross_tenant, _ = self._get("/tenants/tenant-b/records", {"Authorization": "Bearer tok-alice"})
        self.assertEqual(code_cross_tenant, 403)

        code_admin_own, _ = self._get("/tenants/tenant-b/admin-export", {"Authorization": "Bearer tok-bob"})
        self.assertEqual(code_admin_own, 200)

        # Verify audit logs contain zero raw bearer tokens
        serialized = json.dumps(AuthPolicyHandler.audit_log)
        self.assertNotIn("tok-alice", serialized)
        self.assertNotIn("tok-bob", serialized)
        self.assertIn("[REDACTED]", serialized)


if __name__ == "__main__":
    unittest.main()
