"""Idempotency and tenant-scoped key safety.

`IdempotencyCases` is the executable SQLite reference documented in SKILL.md section 4: no shipped
script implements transactional idempotency, so it checks the documented database pattern itself.
`TenantScopedKeyGateTests` exercises the shipped `cache_policy_verifier.py` gate.
"""
from __future__ import annotations

import importlib.util
import json
import math
import sqlite3
import subprocess
import sys
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
from pathlib import Path
from types import ModuleType
from typing import Any

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "cache_policy_verifier.py"


def _load_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("cache_policy_verifier_idempotency", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load {SCRIPT_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


cpv = _load_module()

GOOD_KEY: dict[str, Any] = {
    "pattern": "prod:tenant_{tenant_id}:user_{principal_id}:idem:v1:{idempotency_key}",
    "multi_tenant": True,
    "ttl_sec": 86400,
    "high_traffic": True,
    "jitter_ratio": 0.1,
    "expensive_loader": True,
    "singleflight": True,
}


def _key(**overrides: object) -> dict[str, Any]:
    entry: dict[str, Any] = dict(GOOD_KEY)
    entry.update(overrides)
    return {"redis_keys": [entry]}


def _codes(config: object) -> set[str]:
    return {v["code"] for v in cpv.check_cache_config(config)}


class IdempotencyCases(unittest.TestCase):
    def setUp(self):
        root = tempfile.TemporaryDirectory()
        self.addCleanup(root.cleanup)
        self.path = Path(root.name) / "orders.db"
        db = sqlite3.connect(self.path)
        self.addCleanup(db.close)
        db.executescript("""
            CREATE TABLE orders (id INTEGER PRIMARY KEY, amount INTEGER);
            CREATE TABLE receipts (tenant TEXT, principal TEXT, token TEXT, digest TEXT, order_id INTEGER,
                                   PRIMARY KEY (tenant, principal, token));
        """)
        self.db = db

    def order(self, amount=100, tenant="A", principal="P", allowed=True, abort=False):
        if not allowed:
            return "forbidden", None
        # The operation owns this table. The amount is the sole validated business input.
        digest = sha256(json.dumps({"amount": amount}).encode()).hexdigest()
        db = sqlite3.connect(self.path)
        try:
            with db:
                db.execute("BEGIN IMMEDIATE")
                key = (tenant, principal, "retry-key")
                row = db.execute("SELECT digest, order_id FROM receipts WHERE tenant=? AND principal=? AND token=?", key).fetchone()
                if row:
                    return ("replayed", row[1]) if row[0] == digest else ("conflict", None)
                order_id = db.execute("INSERT INTO orders (amount) VALUES (?)", (amount,)).lastrowid
                if abort:
                    raise RuntimeError("interrupted before receipt")
                db.execute("INSERT INTO receipts VALUES (?, ?, ?, ?, ?)", (*key, digest, order_id))
                return "created", order_id
        finally:
            db.close()

    def test_concurrent_retry_commits_once(self):
        barrier = threading.Barrier(2)
        def submit():
            barrier.wait(timeout=3)
            return self.order()
        with ThreadPoolExecutor(2) as executor:
            futures = [executor.submit(submit) for _ in range(2)]
            results = sorted(f.result() for f in futures)
        self.assertEqual(results, [("created", 1), ("replayed", 1)])
        self.assertEqual(self.db.execute("SELECT count(*) FROM orders").fetchone(), (1,))

    def test_changed_payload_and_authority(self):
        self.order()
        self.assertEqual(self.order(amount=101), ("conflict", None))
        self.assertEqual(self.order(allowed=False), ("forbidden", None))
        self.assertEqual(self.order(tenant="B"), ("created", 2))
        self.assertEqual(self.order(principal="Q"), ("created", 3))

    def test_interruption_before_commit_and_lost_reply_after_commit(self):
        with self.assertRaises(RuntimeError):
            self.order(abort=True)
        self.assertEqual(self.db.execute("SELECT count(*) FROM orders").fetchone(), (0,))
        self.order()
        self.assertEqual(self.order(), ("replayed", 1))


class TenantScopedKeyGateTests(unittest.TestCase):
    def test_tenant_principal_scoped_versioned_key_passes(self) -> None:
        self.assertEqual(cpv.check_cache_config(_key()), [])

    def test_global_key_without_tenant_or_principal_fails(self) -> None:
        self.assertIn("MISSING_TENANT_NAMESPACE", _codes(_key(pattern="prod:idem:v1:{idempotency_key}")))

    def test_unversioned_key_fails(self) -> None:
        self.assertIn("MISSING_SCHEMA_VERSION", _codes(_key(pattern="prod:tenant_{tenant_id}:idem:{key}")))

    def test_empty_pattern_fails(self) -> None:
        self.assertEqual(_codes(_key(pattern="  ")), {"EMPTY_KEY_PATTERN"})

    def test_string_flags_are_invalid_input(self) -> None:
        for field in ("multi_tenant", "persistent_structure", "high_traffic", "expensive_loader", "singleflight"):
            for bad in ("false", "true"):
                with self.subTest(field=field, bad=bad):
                    with self.assertRaises(ValueError):
                        cpv.check_cache_config(_key(**{field: bad}))

    def test_ttl_must_be_positive_finite_number(self) -> None:
        self.assertEqual(cpv.check_cache_config(_key(ttl_sec=1)), [])
        for bad in (0, -5, "300", None, True, math.inf):
            with self.subTest(bad=bad):
                self.assertIn("MISSING_OR_ZERO_TTL", _codes(_key(ttl_sec=bad)))

    def test_persistent_structure_skips_ttl(self) -> None:
        self.assertEqual(cpv.check_cache_config(_key(ttl_sec=None, persistent_structure=True)), [])

    def test_hot_key_jitter_must_be_positive_number(self) -> None:
        for bad in (0, "0.1", True, None):
            with self.subTest(bad=bad):
                self.assertIn("MISSING_TTL_JITTER", _codes(_key(jitter_ratio=bad)))

    def test_expensive_loader_needs_stampede_defense(self) -> None:
        self.assertIn("MISSING_STAMPEDE_DEFENSE", _codes(_key(singleflight=False)))
        self.assertEqual(cpv.check_cache_config(_key(singleflight=False, stale_while_revalidate=True)), [])

    def test_forbidden_redis_commands_fail(self) -> None:
        self.assertIn("FORBIDDEN_REDIS_COMMAND", _codes(_key(invalidation_command="KEYS *idem*")))
        self.assertIn("FORBIDDEN_REDIS_COMMAND", _codes({"redis_keys": [GOOD_KEY], "redis_commands": ["FLUSHALL"]}))
        self.assertEqual(cpv.check_cache_config(_key(invalidation_command="DEL prod:tenant_1:idem:v1:k")), [])

    def test_redis_commands_must_be_an_array(self) -> None:
        for bad in ("FLUSHDB", 7, {"cmd": "FLUSHDB"}):
            with self.subTest(bad=bad):
                self.assertIn("INVALID_REDIS_COMMANDS", _codes({"redis_keys": [GOOD_KEY], "redis_commands": bad}))

    def test_empty_or_wrong_type_config_fails(self) -> None:
        for bad in ({}, None, [], "redis_keys", {"redis_keys": []}, {"unrelated": True}):
            with self.subTest(bad=bad):
                self.assertEqual(_codes(bad), {"EMPTY_CONFIG"})
        self.assertIn("INVALID_REDIS_KEYS", _codes({"redis_keys": "prod:tenant_1:v1"}))
        self.assertIn("INVALID_REDIS_ENTRY", _codes({"redis_keys": ["prod:tenant_1:v1"]}))


class L1AndHttpGateTests(unittest.TestCase):
    def test_bounded_l1_cache_passes_and_unbounded_fails(self) -> None:
        self.assertEqual(cpv.check_cache_config({"l1_caches": [{"name": "jwks", "max_entries": 10, "ttl_sec": 60}]}), [])
        for max_entries, ttl in ((0, 60), (10, 0), (True, 60), ("10", 60), (10, True), (None, None)):
            with self.subTest(max_entries=max_entries, ttl=ttl):
                self.assertTrue(_codes({"l1_caches": [{"name": "c", "max_entries": max_entries, "ttl_sec": ttl}]}) & {"UNBOUNDED_L1_CACHE", "UNBOUNDED_L1_TTL"})

    def test_private_route_headers(self) -> None:
        ok = {"http_routes": [{"path": "/me", "authenticated": True, "cache_control": "private, no-store"}]}
        self.assertEqual(cpv.check_cache_config(ok), [])
        for cc in ("public, max-age=60", "max-age=60, s-maxage=60", "max-age=60", ""):
            with self.subTest(cc=cc):
                self.assertTrue(_codes({"http_routes": [{"path": "/me", "authenticated": True, "cache_control": cc}]}))
        with self.assertRaises(ValueError):
            cpv.check_cache_config({"http_routes": [{"path": "/me", "authenticated": "true", "cache_control": "public"}]})

    def test_long_public_ttl_requires_invalidation_hook(self) -> None:
        route: dict[str, Any] = {"path": "/catalog", "cache_control": "public, max-age=86400", "max_age_sec": 86400}
        self.assertIn("LONG_PUBLIC_TTL_NO_INVALIDATION", _codes({"http_routes": [route]}))
        self.assertEqual(cpv.check_cache_config({"http_routes": [dict(route, etag=True)]}), [])
        self.assertEqual(cpv.check_cache_config({"http_routes": [dict(route, max_age_sec=300)]}), [])


class CliTests(unittest.TestCase):
    def _run(self, payload: object) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "cache.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            return subprocess.run(
                [sys.executable, "-B", str(SCRIPT_PATH), "--check-cache-config", str(path)],
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )

    def test_cli_exit_codes(self) -> None:
        self.assertEqual(self._run(_key()).returncode, 0)
        self.assertEqual(self._run(_key(ttl_sec=0)).returncode, 1)
        self.assertEqual(self._run({}).returncode, 1)
        invalid = self._run(_key(multi_tenant="false"))
        self.assertEqual(invalid.returncode, 2)
        self.assertIn("INVALID_INPUT", invalid.stdout)


if __name__ == "__main__":
    unittest.main()
