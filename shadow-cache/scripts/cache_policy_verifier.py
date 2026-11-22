#!/usr/bin/env python3
"""Deterministic multi-tier cache policy verifier for shadow-cache.

Audits Redis key tenant partitioning & schema versioning, TTL + jitter, singleflight
stampede protection, forbidden prod commands (KEYS/FLUSHDB), HTTP Cache-Control PII safety,
public catalog Surrogate-Key/ETag invalidation, and bounded L1 in-process caches.
Zero external dependencies (Python stdlib only).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

TENANT_SEGMENT_RE = re.compile(r"(?:tenant[_a-z0-9-]*|\{tenant[_a-z]*\}|user[_a-z0-9-]*|\{user[_a-z]*\})", re.IGNORECASE)
VERSION_SEGMENT_RE = re.compile(r":v(?:\d+|\{[a-z_]+\})(?::|$)", re.IGNORECASE)
DANGEROUS_REDIS_CMD_RE = re.compile(r"\b(?:KEYS\s+\*|KEYS\s+['\"]?\*|FLUSHDB|FLUSHALL)\b", re.IGNORECASE)


def check_cache_config(config: Any) -> list[dict[str, str]]:
    """Validate multi-tier cache configuration (Redis L2, HTTP/CDN L0, in-process L1)."""
    violations: list[dict[str, str]] = []
    if not isinstance(config, dict) or not config:
        return [{"code": "EMPTY_CONFIG", "detail": "Cache configuration must be a non-empty JSON object."}]

    # 1. Redis / Valkey L2 keys & commands
    redis_keys = config.get("redis_keys", [])
    if not isinstance(redis_keys, list):
        violations.append({"code": "INVALID_REDIS_KEYS", "detail": "`redis_keys` must be an array."})
    else:
        for idx, entry in enumerate(redis_keys):
            if not isinstance(entry, dict):
                violations.append({"code": "INVALID_REDIS_ENTRY", "detail": f"redis_keys[{idx}] must be an object."})
                continue
            pattern = str(entry.get("pattern", "")).strip()
            scope = str(entry.get("scope", "tenant")).lower()
            multi_tenant = bool(entry.get("multi_tenant", scope != "public"))

            if not pattern:
                violations.append({"code": "EMPTY_KEY_PATTERN", "detail": f"redis_keys[{idx}] missing `pattern`."})
                continue

            if multi_tenant and not TENANT_SEGMENT_RE.search(pattern):
                violations.append({
                    "code": "MISSING_TENANT_NAMESPACE",
                    "detail": f"Multi-tenant Redis key `{pattern}` lacks tenant/user scope segment (cross-tenant leakage risk).",
                })

            if not VERSION_SEGMENT_RE.search(pattern):
                violations.append({
                    "code": "MISSING_SCHEMA_VERSION",
                    "detail": f"Redis key `{pattern}` lacks explicit schema version segment (e.g. `:v1:`) for safe deploy rollouts.",
                })

            persistent = bool(entry.get("persistent_structure", False))
            ttl_sec = entry.get("ttl_sec")
            if not persistent:
                if not isinstance(ttl_sec, (int, float)) or ttl_sec <= 0:
                    violations.append({
                        "code": "MISSING_OR_ZERO_TTL",
                        "detail": f"Redis key `{pattern}` must set a positive finite `ttl_sec`.",
                    })

            bulk_or_hot = bool(entry.get("bulk_warmed", False) or entry.get("high_traffic", False))
            jitter_ratio = entry.get("jitter_ratio", 0)
            if bulk_or_hot and (not isinstance(jitter_ratio, (int, float)) or jitter_ratio <= 0):
                violations.append({
                    "code": "MISSING_TTL_JITTER",
                    "detail": f"Bulk-warmed/high-traffic key `{pattern}` requires positive `jitter_ratio` (e.g. 0.1–0.2) to prevent cache avalanche.",
                })

            if bool(entry.get("expensive_loader", False)):
                has_defense = bool(
                    entry.get("singleflight", False)
                    or entry.get("mutex_lock", False)
                    or entry.get("stale_while_revalidate", False)
                )
                if not has_defense:
                    violations.append({
                        "code": "MISSING_STAMPEDE_DEFENSE",
                        "detail": f"Expensive hot key `{pattern}` lacks `singleflight`, `mutex_lock`, or `stale_while_revalidate` stampede protection.",
                    })

            inv_cmd = str(entry.get("invalidation_command", ""))
            if inv_cmd and DANGEROUS_REDIS_CMD_RE.search(inv_cmd):
                violations.append({
                    "code": "FORBIDDEN_REDIS_COMMAND",
                    "detail": f"Redis key `{pattern}` uses blocking/destructive command `{inv_cmd}`; use explicit key deletion, generation tokens, or SCAN.",
                })

    for raw_cmd in config.get("redis_commands", []):
        if isinstance(raw_cmd, str) and DANGEROUS_REDIS_CMD_RE.search(raw_cmd):
            violations.append({
                "code": "FORBIDDEN_REDIS_COMMAND",
                "detail": f"Forbidden production Redis command `{raw_cmd}` blocks the event loop or wipes unrelated tenants.",
            })

    # 2. HTTP / CDN Edge L0 routes
    http_routes = config.get("http_routes", [])
    if not isinstance(http_routes, list):
        violations.append({"code": "INVALID_HTTP_ROUTES", "detail": "`http_routes` must be an array."})
    else:
        for idx, route in enumerate(http_routes):
            if not isinstance(route, dict):
                violations.append({"code": "INVALID_HTTP_ROUTE", "detail": f"http_routes[{idx}] must be an object."})
                continue
            path = str(route.get("path", f"http_routes[{idx}]"))
            cc = str(route.get("cache_control", "")).lower()
            authenticated = bool(route.get("authenticated", False))
            contains_pii = bool(route.get("contains_pii", False))

            if authenticated or contains_pii:
                if "public" in cc or "s-maxage" in cc:
                    violations.append({
                        "code": "PUBLIC_CACHE_ON_PRIVATE_ROUTE",
                        "detail": f"Authenticated/PII route `{path}` sets public/shared CDN caching (`{route.get('cache_control')}`); leaks user data across CDN edge.",
                    })
                elif "private" not in cc and "no-store" not in cc:
                    violations.append({
                        "code": "MISSING_PRIVATE_NO_STORE",
                        "detail": f"Authenticated/PII route `{path}` must explicitly set `Cache-Control: private, no-store` (or `private, no-cache`).",
                    })
            else:
                max_age = route.get("max_age_sec", 0)
                if "public" in cc and isinstance(max_age, (int, float)) and max_age > 300:
                    has_inv = bool(
                        route.get("surrogate_key")
                        or route.get("etag")
                        or route.get("content_hashed_url")
                    )
                    if not has_inv:
                        violations.append({
                            "code": "LONG_PUBLIC_TTL_NO_INVALIDATION",
                            "detail": f"Public route `{path}` caches for `{max_age}s` without `surrogate_key`, `etag`, or content-hashed URLs (risks long stale catalog views).",
                        })

    # 3. In-Process L1 Caches
    l1_caches = config.get("l1_caches", [])
    if not isinstance(l1_caches, list):
        violations.append({"code": "INVALID_L1_CACHES", "detail": "`l1_caches` must be an array."})
    else:
        for idx, cache in enumerate(l1_caches):
            if not isinstance(cache, dict):
                violations.append({"code": "INVALID_L1_ENTRY", "detail": f"l1_caches[{idx}] must be an object."})
                continue
            name = str(cache.get("name", f"l1_caches[{idx}]"))
            max_entries = cache.get("max_entries")
            if not isinstance(max_entries, int) or max_entries <= 0:
                violations.append({
                    "code": "UNBOUNDED_L1_CACHE",
                    "detail": f"In-process L1 cache `{name}` lacks a positive `max_entries` LRU cap (OOM leak risk).",
                })
            ttl_sec = cache.get("ttl_sec")
            if not isinstance(ttl_sec, (int, float)) or ttl_sec <= 0:
                violations.append({
                    "code": "UNBOUNDED_L1_TTL",
                    "detail": f"In-process L1 cache `{name}` must declare a bounded positive `ttl_sec`.",
                })

    return violations


def run_self_test() -> dict[str, Any]:
    probes: list[tuple[str, bool]] = []

    # PRECISION-1: Clean multi-tier config passes
    v = check_cache_config({
        "redis_keys": [
            {
                "pattern": "prod:tenant_{tenant_id}:orders:v1:{order_id}",
                "multi_tenant": True,
                "ttl_sec": 300,
                "high_traffic": True,
                "jitter_ratio": 0.15,
                "expensive_loader": True,
                "singleflight": True,
            }
        ],
        "http_routes": [
            {"path": "/api/v1/me/profile", "authenticated": True, "contains_pii": True, "cache_control": "private, no-store"},
            {"path": "/catalog/products", "authenticated": False, "cache_control": "public, max-age=60, s-maxage=86400, stale-while-revalidate=30", "max_age_sec": 86400, "surrogate_key": "catalog:products"},
        ],
        "l1_caches": [
            {"name": "jwks_keys", "max_entries": 256, "ttl_sec": 60}
        ],
    })
    probes.append(("PRECISION-1: Tenant-scoped Redis, private auth HTTP, Surrogate-Key CDN & bounded L1 pass", len(v) == 0))

    # RECALL-1: Global multi-tenant key & missing schema version rejected
    v = check_cache_config({
        "redis_keys": [{"pattern": "orders:list", "multi_tenant": True, "ttl_sec": 120}]
    })
    codes = {item["code"] for item in v}
    probes.append((
        "RECALL-1: Rejects global multi-tenant key without tenant scope & schema version",
        {"MISSING_TENANT_NAMESPACE", "MISSING_SCHEMA_VERSION"}.issubset(codes),
    ))

    # RECALL-2: Public Cache-Control on authenticated/PII endpoint rejected
    v = check_cache_config({
        "http_routes": [
            {"path": "/api/v1/orders", "authenticated": True, "cache_control": "public, max-age=3600"}
        ]
    })
    codes = {item["code"] for item in v}
    probes.append(("RECALL-2: Rejects public Cache-Control on authenticated route", "PUBLIC_CACHE_ON_PRIVATE_ROUTE" in codes))

    # RECALL-3: KEYS * / FLUSHDB & missing TTL rejected
    v = check_cache_config({
        "redis_keys": [
            {
                "pattern": "prod:tenant_{tenant_id}:catalog:v1:list",
                "invalidation_command": "KEYS *catalog*",
            }
        ],
        "redis_commands": ["FLUSHDB"],
    })
    codes = {item["code"] for item in v}
    probes.append((
        "RECALL-3: Rejects KEYS */FLUSHDB & missing finite TTL",
        {"FORBIDDEN_REDIS_COMMAND", "MISSING_OR_ZERO_TTL"}.issubset(codes),
    ))

    # RECALL-4: Expensive hot key without singleflight & bulk-warmed without jitter rejected
    v = check_cache_config({
        "redis_keys": [
            {
                "pattern": "prod:tenant_{tenant_id}:dashboard:v1:kpi",
                "ttl_sec": 600,
                "bulk_warmed": True,
                "expensive_loader": True,
            }
        ]
    })
    codes = {item["code"] for item in v}
    probes.append((
        "RECALL-4: Rejects expensive key without stampede defense & bulk key without jitter",
        {"MISSING_STAMPEDE_DEFENSE", "MISSING_TTL_JITTER"}.issubset(codes),
    ))

    # RECALL-5: Unbounded L1 Map & 24h public catalog without Surrogate-Key/ETag rejected
    v = check_cache_config({
        "http_routes": [
            {"path": "/products", "authenticated": False, "cache_control": "public, max-age=86400", "max_age_sec": 86400}
        ],
        "l1_caches": [{"name": "raw_map_cache", "max_entries": 0, "ttl_sec": 0}],
    })
    codes = {item["code"] for item in v}
    probes.append((
        "RECALL-5: Rejects unbounded L1 cache & long public TTL without invalidation hook",
        {"UNBOUNDED_L1_CACHE", "UNBOUNDED_L1_TTL", "LONG_PUBLIC_TTL_NO_INVALIDATION"}.issubset(codes),
    ))

    # BOUNDARY-1: Empty config rejected gracefully
    v = check_cache_config({})
    probes.append(("BOUNDARY-1: Rejects empty config gracefully", len(v) == 1 and v[0]["code"] == "EMPTY_CONFIG"))

    passed = sum(1 for _, ok in probes if ok)
    return {
        "tool": "cache_policy_verifier.py",
        "total_probes": len(probes),
        "passed": passed,
        "failed": len(probes) - passed,
        "all_passed": passed == len(probes),
        "results": [{"probe": name, "passed": ok} for name, ok in probes],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify multi-tier caching safety policies (L0 HTTP/CDN, L1 LRU, L2 Redis).")
    parser.add_argument("--self-test", action="store_true", help="Run built-in precision/recall falsification probes.")
    parser.add_argument("--check-cache-config", type=Path, help="Path to JSON cache policy config.")
    args = parser.parse_args(argv)

    if args.self_test:
        report = run_self_test()
        print(json.dumps(report, indent=2))
        return 0 if report["all_passed"] else 1

    if not args.check_cache_config:
        parser.print_help()
        return 2

    data = json.loads(args.check_cache_config.read_text(encoding="utf-8"))
    violations = check_cache_config(data)
    output = {"status": "PASS" if not violations else "FAIL", "violation_count": len(violations), "violations": violations}
    print(json.dumps(output, indent=2))
    return 0 if not violations else 1


if __name__ == "__main__":
    sys.exit(main())
