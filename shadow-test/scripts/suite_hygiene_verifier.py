#!/usr/bin/env python3
"""Deterministic polyglot test hygiene & teardown verifier for shadow-test.

Audits test suites/manifests for:
  1. Flaky wall-clock sleeps (time.sleep / setTimeout / waitForTimeout) without fake timers
  2. Strict TypeScript test typing violations (`: any`, `as Type` casts)
  3. Ephemeral Docker test container hygiene (`--rm`, `--label shadow.ephemeral=true`, try/finally or trap teardown)
  4. Universal 8-point HTTP endpoint test surface coverage (happy, validation, 401, 403/IDOR, 404, 409, boundary, cleanup)
Zero external dependencies (Python stdlib only).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

FLAKY_SLEEP_RE = re.compile(
    r"(?:\btime\.sleep\s*\(|\bsetTimeout\s*\([^,]+,\s*\d{3,}|\bwaitForTimeout\s*\(|\bThread\.sleep\s*\(|\bsleep\s+[1-9]\d*)",
    re.IGNORECASE,
)
TS_ANY_RE = re.compile(r"(?::\s*any\b|\bany\[\]|<any>)")
TS_CAST_RE = re.compile(r"\bas\s+(?!const\b)[A-Z][A-Za-z0-9_<>\[\]| ]*")
DOCKER_RUN_RE = re.compile(r"\bdocker\s+run\b[^\n]*", re.IGNORECASE)

REQUIRED_HTTP_SURFACES = frozenset({
    "happy_path",
    "validation_4xx",
    "unauthenticated_401",
    "forbidden_idor_403",
    "not_found_404",
    "conflict_idempotency_409",
    "boundary_values",
    "state_cleanup",
})


def check_test_hygiene(spec: Any) -> list[dict[str, str]]:
    """Audit a test suite manifest or snippet set for determinism, strict typing, teardown, and coverage."""
    violations: list[dict[str, str]] = []
    if not isinstance(spec, dict) or not spec:
        return [{"code": "EMPTY_SPEC", "detail": "Test hygiene spec must be a non-empty JSON object."}]

    snippets = spec.get("test_snippets", [])
    if not isinstance(snippets, list):
        violations.append({"code": "INVALID_SNIPPETS", "detail": "`test_snippets` must be an array."})
    else:
        for idx, item in enumerate(snippets):
            if not isinstance(item, dict):
                violations.append({"code": "INVALID_SNIPPET_ENTRY", "detail": f"test_snippets[{idx}] must be an object."})
                continue
            name = str(item.get("file", f"snippet[{idx}]"))
            lang = str(item.get("language", "")).lower()
            code = str(item.get("code", ""))
            uses_fake_timers = bool(item.get("uses_fake_timers", False))

            if FLAKY_SLEEP_RE.search(code) and not uses_fake_timers:
                violations.append({
                    "code": "FLAKY_WALL_CLOCK_SLEEP",
                    "detail": f"`{name}` uses raw sleep/waitForTimeout without fake timers or deterministic event synchronization.",
                })

            if lang in {"ts", "typescript", "tsx"}:
                if TS_ANY_RE.search(code):
                    violations.append({
                        "code": "TS_STRICT_ANY_VIOLATION",
                        "detail": f"`{name}` uses forbidden `any` type in TypeScript test; use typed factories instead.",
                    })
                if TS_CAST_RE.search(code):
                    violations.append({
                        "code": "TS_STRICT_CAST_VIOLATION",
                        "detail": f"`{name}` uses forbidden `as Type` cast in TypeScript test; narrow or build typed fixtures instead.",
                    })

            if DOCKER_RUN_RE.search(code):
                has_rm = "--rm" in code
                has_label = "shadow.ephemeral=true" in code
                has_teardown = bool(re.search(r"\b(?:finally|trap\s+.*EXIT|afterAll)\b", code, re.IGNORECASE)) and bool(
                    re.search(r"docker\s+(?:rm\s+-f|compose\b.*\bdown)", code, re.IGNORECASE)
                )
                if not has_rm or not has_label:
                    violations.append({
                        "code": "DOCKER_MISSING_EPHEMERAL_FLAGS",
                        "detail": f"`{name}` spawns Docker test container without both `--rm` and `--label shadow.ephemeral=true`.",
                    })
                if not has_teardown:
                    violations.append({
                        "code": "DOCKER_MISSING_GUARANTEED_TEARDOWN",
                        "detail": f"`{name}` spawns Docker container without guaranteed `finally`/`trap EXIT` teardown (`docker rm -f -v`).",
                    })

    endpoint_tests = spec.get("http_endpoint_suites", [])
    if not isinstance(endpoint_tests, list):
        violations.append({"code": "INVALID_HTTP_SUITES", "detail": "`http_endpoint_suites` must be an array."})
    else:
        for idx, suite in enumerate(endpoint_tests):
            if not isinstance(suite, dict):
                violations.append({"code": "INVALID_HTTP_SUITE", "detail": f"http_endpoint_suites[{idx}] must be an object."})
                continue
            ep = str(suite.get("endpoint", f"endpoint[{idx}]"))
            covered = {str(s).strip().lower() for s in suite.get("covered_surfaces", [])}
            applicable_exemptions = {str(s).strip().lower() for s in suite.get("not_applicable", [])}
            missing = sorted(REQUIRED_HTTP_SURFACES - covered - applicable_exemptions)
            if missing:
                violations.append({
                    "code": "INCOMPLETE_ENDPOINT_COVERAGE",
                    "detail": f"Endpoint `{ep}` missing required failure-surface tests: {missing}.",
                })

    return violations


def run_self_test() -> dict[str, Any]:
    probes: list[tuple[str, bool]] = []

    # PRECISION-1: Clean TS integration test, leak-proof Docker harness, and 8-point HTTP coverage pass
    v = check_test_hygiene({
        "test_snippets": [
            {
                "file": "tests/orders.test.ts",
                "language": "ts",
                "code": "const order: Order = createTestOrder({ status: 'PENDING' }); expect(res.status).toBe(201);",
            },
            {
                "file": "scripts/run_db_tests.ps1",
                "language": "powershell",
                "code": "try { docker run -d --rm --label shadow.ephemeral=true --name app-test-1 postgres:16 } finally { docker rm -f -v app-test-1 }",
            },
        ],
        "http_endpoint_suites": [
            {
                "endpoint": "POST /api/v1/orders",
                "covered_surfaces": sorted(REQUIRED_HTTP_SURFACES),
            }
        ],
    })
    probes.append(("PRECISION-1: Clean TS test, leak-proof Docker harness & 8-point HTTP coverage pass", len(v) == 0))

    # RECALL-1: Raw sleep / waitForTimeout rejected
    v = check_test_hygiene({
        "test_snippets": [
            {"file": "tests/worker.test.py", "language": "python", "code": "enqueue_job(); time.sleep(3); assert job_done()"}
        ]
    })
    codes = {x["code"] for x in v}
    probes.append(("RECALL-1: Rejects flaky raw time.sleep() synchronization", "FLAKY_WALL_CLOCK_SLEEP" in codes))

    # RECALL-2: TS any and as Type casts in test rejected
    v = check_test_hygiene({
        "test_snippets": [
            {"file": "tests/calc.test.ts", "language": "ts", "code": "const payload: any = {}; const res = parse(payload) as OrderDto;"}
        ]
    })
    codes = {x["code"] for x in v}
    probes.append((
        "RECALL-2: Rejects forbidden `any` and `as Type` casts in TS tests",
        {"TS_STRICT_ANY_VIOLATION", "TS_STRICT_CAST_VIOLATION"}.issubset(codes),
    ))

    # RECALL-3: Docker container without --rm, shadow.ephemeral label, or finally teardown rejected
    v = check_test_hygiene({
        "test_snippets": [
            {"file": "scripts/bad_test.sh", "language": "bash", "code": "docker run -d --name leak-db postgres:16\npytest"}
        ]
    })
    codes = {x["code"] for x in v}
    probes.append((
        "RECALL-3: Rejects Docker test harness missing ephemeral flags & guaranteed teardown",
        {"DOCKER_MISSING_EPHEMERAL_FLAGS", "DOCKER_MISSING_GUARANTEED_TEARDOWN"}.issubset(codes),
    ))

    # RECALL-4: Missing 403 IDOR & 409 idempotency on HTTP endpoint rejected
    v = check_test_hygiene({
        "http_endpoint_suites": [
            {"endpoint": "PATCH /api/v1/invoices/:id", "covered_surfaces": ["happy_path", "validation_4xx"]}
        ]
    })
    codes = {x["code"] for x in v}
    probes.append(("RECALL-4: Rejects HTTP suite omitting IDOR/401/409/cleanup surfaces", "INCOMPLETE_ENDPOINT_COVERAGE" in codes))

    # PRECISION-2: Legitimate `as const` in TypeScript test is NOT falsely flagged
    v = check_test_hygiene({
        "test_snippets": [
            {"file": "tests/keys.test.ts", "language": "ts", "code": "const key = ['orders', 'list'] as const; expect(key[0]).toBe('orders');"}
        ]
    })
    probes.append(("PRECISION-2: Legitimate `as const` in TS test passes cleanly", len(v) == 0))

    # BOUNDARY-1: Empty spec rejected gracefully
    v = check_test_hygiene({})
    probes.append(("BOUNDARY-1: Rejects empty test spec gracefully", len(v) == 1 and v[0]["code"] == "EMPTY_SPEC"))

    passed = sum(1 for _, ok in probes if ok)
    return {
        "tool": "suite_hygiene_verifier.py",
        "total_probes": len(probes),
        "passed": passed,
        "failed": len(probes) - passed,
        "all_passed": passed == len(probes),
        "results": [{"probe": name, "passed": ok} for name, ok in probes],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit test determinism, strict typing, Docker teardown, and HTTP coverage surfaces.")
    parser.add_argument("--self-test", action="store_true", help="Run built-in precision/recall falsification probes.")
    parser.add_argument("--check-test-suite", type=Path, help="Path to JSON test hygiene manifest.")
    args = parser.parse_args(argv)

    if args.self_test:
        report = run_self_test()
        print(json.dumps(report, indent=2))
        return 0 if report["all_passed"] else 1

    if not args.check_test_suite:
        parser.print_help()
        return 2

    data = json.loads(args.check_test_suite.read_text(encoding="utf-8"))
    violations = check_test_hygiene(data)
    output = {"status": "PASS" if not violations else "FAIL", "violation_count": len(violations), "violations": violations}
    print(json.dumps(output, indent=2))
    return 0 if not violations else 1


if __name__ == "__main__":
    sys.exit(main())
