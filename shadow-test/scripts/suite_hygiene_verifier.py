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
import shlex
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "shadow-monarch" / "scripts"))
from shadow_input import run_checked_cli, strict_bool

FLAKY_SLEEP_RE = re.compile(
    r"(?:\btime\.sleep\s*\(|\bsetTimeout\s*\([^,]+,\s*\d{3,}|\bwaitForTimeout\s*\(|\bThread\.sleep\s*\(|\bsleep\s+[1-9]\d*)",
    re.IGNORECASE,
)
TS_ANY_RE = re.compile(r"(?::\s*any\b|\bany\[\]|<any>)")
TS_CAST_RE = re.compile(r"\bas\s+(?!const\b)[A-Z][A-Za-z0-9_<>\[\]| ]*")
DOCKER_RUN_RE = re.compile(r"\bdocker\s+run\b([^;\n{}]*)", re.IGNORECASE)
DOCKER_COMMENT_RE = re.compile(
    r"""(?P<quoted>"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*')|/\*[\s\S]*?\*/|<\#[\s\S]*?\#>|(?:^|(?<=[\s;{}]))(?:\#|//)[^\n]*"""
)

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


DOCKER_OPTIONS_WITH_VALUE = {
    "--env", "--env-file", "--label", "--name", "--network", "--platform",
    "--publish", "--tmpfs", "--user", "--volume", "--workdir", "-e", "-p", "-u", "-v", "-w",
}
DOCKER_SWITCHES = {"--detach", "--interactive", "--tty", "--init", "--privileged", "-d", "-i", "-t", "-it"}


def _docker_run_settings(command: str) -> tuple[bool, str | None]:
    try:
        tokens = iter(shlex.split(command))
    except ValueError:
        return False, None
    auto_remove = False
    owned = False
    name = None
    for token in tokens:
        if token == "--":
            return bool(next(tokens, "")) and auto_remove and owned, name
        if not token.startswith("-"):
            return auto_remove and owned, name
        option, separator, value = token.partition("=")
        if option == "--rm":
            auto_remove = not separator or value == "true"
        elif option in DOCKER_OPTIONS_WITH_VALUE:
            value = value if separator else next(tokens, "")
            if option == "--label" and value.partition("=")[0] == "shadow.ephemeral":
                owned = value == "shadow.ephemeral=true"
            elif option == "--name":
                name = value
        elif option not in DOCKER_SWITCHES:
            return False, None
    return False, name


def _docker_cleanup_targets(code: str) -> set[str]:
    bodies = re.findall(r"(?:^|[;\n}])\s*(?:finally\s*|afterAll\s*\([^{}]*?)\{([^{}]*)\}", code, re.IGNORECASE)
    for trap in re.findall(r"""(?:^|[;\n])\s*trap\s+("[^"\n]+"|'[^'\n]+'|[\w-]+)\s+EXIT\b""", code):
        if trap[0] in ('"', "'"):
            bodies.append(trap[1:-1])
        else:
            body = re.search(rf"(?m)^\s*{re.escape(trap)}\s*\(\s*\)\s*\{{([^{{}}]*)\}}", code)
            if body:
                bodies.append(body[1])
    targets: set[str] = set()
    for body in bodies:
        for args in re.findall(r"(?:^|[;\n])\s*docker\s+rm\s+([^;\n|><]+)", body, re.IGNORECASE):
            try:
                tokens = shlex.split(args)
            except ValueError:
                continue
            options = {token for token in tokens if token.startswith("-")}
            force = bool(options & {"-f", "-fv", "-vf", "--force"})
            volumes = bool(options & {"-v", "-fv", "-vf", "--volumes"})
            if force and volumes:
                targets.update(token for token in tokens if not token.startswith("-"))
    return targets


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
            uses_fake_timers = strict_bool(item.get("uses_fake_timers", False), "uses_fake_timers")

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

            docker_code = DOCKER_COMMENT_RE.sub(lambda match: match["quoted"] or " ", code)
            docker_code = docker_code.replace("\\\n", " ").replace("`" + "\n", " ")
            runs = DOCKER_RUN_RE.findall(docker_code)
            if runs:
                settings = [_docker_run_settings(command) for command in runs]
                if not all(has_flags for has_flags, _ in settings):
                    violations.append({
                        "code": "DOCKER_MISSING_EPHEMERAL_FLAGS",
                        "detail": f"`{name}` spawns Docker test container without both `--rm` and `--label shadow.ephemeral=true`.",
                    })
                targets = _docker_cleanup_targets(docker_code)
                if not targets or any(name and name not in targets for _, name in settings):
                    violations.append({
                        "code": "DOCKER_MISSING_GUARANTEED_TEARDOWN",
                        "detail": f"`{name}` spawns Docker container without matching `finally`/`trap EXIT` teardown (`docker rm -f -v`).",
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
    sys.exit(run_checked_cli(main))
