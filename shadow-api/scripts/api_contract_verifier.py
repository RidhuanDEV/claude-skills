#!/usr/bin/env python3
"""Deterministic API Contract, RFC 9457, Pagination, Idempotency & Breaking-Diff Verifier (L0/L1 offline CLI).

Zero third-party dependencies (Python 3 stdlib only).
Validates:
  - RFC 9457 application/problem+json error envelopes & zero stack/SQL leaks (--check-problem-json)
  - OpenAPI 3.x contract hygiene: operationId, pagination bounds, Idempotency-Key, Deprecation/Sunset (--check-openapi-contract)
  - Backward-compatibility breaking-diff detection between v1 and v2 specs (--check-breaking-diff)
  - Built-in precision & recall self-test probes (--self-test)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

LEAK_PATTERNS = re.compile(
    r"(?:Traceback \(most recent call last\)|at\s+[A-Za-z0-9_$.]+\s+\([^)]+:\d+:\d+\)|"
    r"SELECT\s+.+\s+FROM\s+|SQLSTATE\[|psycopg2|PrismaClientKnownRequestError|pg_catalog)",
    re.IGNORECASE,
)


def check_problem_json(payload: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []

    content_type = str(payload.get("content_type", "application/problem+json")).lower()
    if "application/problem+json" not in content_type:
        errors.append(f"Content-Type must be 'application/problem+json' (got '{content_type}').")

    body = payload.get("body", payload)
    if not isinstance(body, dict):
        return {"check": "problem_json", "passed": False, "errors": ["Body must be a JSON object."], "warnings": []}

    for req_field in ("type", "title", "status"):
        if req_field not in body or body[req_field] in (None, ""):
            errors.append(f"RFC 9457 problem response missing required member '{req_field}'.")

    status = body.get("status")
    if not isinstance(status, int) or not (400 <= status <= 599):
        errors.append(f"RFC 9457 'status' must be an HTTP 4xx/5xx integer (got {status!r}).")

    serialized = json.dumps(body)
    if LEAK_PATTERNS.search(serialized):
        errors.append("Internal stack trace or raw SQL/ORM error leaked inside API error response.")

    if "stack" in body or "stackTrace" in body:
        errors.append("Forbidden 'stack'/'stackTrace' field exposed in API error response.")

    if "instance" not in body and "requestId" not in body and "traceId" not in body:
        warnings.append("Include 'instance' or 'requestId'/'traceId' for log correlation.")

    return {"check": "problem_json", "passed": len(errors) == 0, "errors": errors, "warnings": warnings}


def check_openapi_contract(spec: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []

    openapi_ver = str(spec.get("openapi", ""))
    if not openapi_ver.startswith(("3.0.", "3.1.")):
        errors.append(f"Expected OpenAPI 3.0.x or 3.1.x specification (got '{openapi_ver}').")

    paths = spec.get("paths", {})
    if not isinstance(paths, dict) or len(paths) == 0:
        errors.append("OpenAPI spec must declare at least 1 path.")
        return {"check": "openapi_contract", "passed": False, "errors": errors, "warnings": warnings}

    seen_op_ids: set[str] = set()
    for path, path_item in paths.items():
        if not isinstance(path_item, dict):
            continue
        for method, op in path_item.items():
            m = method.lower()
            if m not in {"get", "post", "put", "patch", "delete"} or not isinstance(op, dict):
                continue

            op_id = op.get("operationId")
            if not isinstance(op_id, str) or not op_id.strip():
                errors.append(f"{m.upper()} {path}: missing 'operationId'.")
            elif op_id in seen_op_ids:
                errors.append(f"{m.upper()} {path}: duplicate operationId '{op_id}'.")
            else:
                seen_op_ids.add(op_id)

            params = op.get("parameters", [])
            param_names = {str(p.get("name", "")).lower(): p for p in params if isinstance(p, dict)}

            # Check bounded pagination on collection GET endpoints
            if m == "get" and op.get("x-collection", False):
                limit_param = param_names.get("limit") or param_names.get("page_size")
                if not limit_param:
                    errors.append(f"GET {path}: collection endpoint missing bounded 'limit'/'page_size' parameter.")
                else:
                    schema = limit_param.get("schema", {})
                    max_val = schema.get("maximum") if isinstance(schema, dict) else None
                    if not isinstance(max_val, int) or max_val > 100:
                        errors.append(f"GET {path}: pagination maximum must be explicitly bounded <= 100 (got {max_val!r}).")

            # Check Idempotency-Key on non-idempotent payment/order creation POST routes
            if m == "post" and op.get("x-requires-idempotency", False):
                if "idempotency-key" not in param_names:
                    errors.append(f"POST {path}: mutating/financial create endpoint missing 'Idempotency-Key' header parameter.")

            # Check RFC 9745 Deprecation / Sunset metadata when deprecated: true
            if op.get("deprecated") is True:
                responses = op.get("responses", {})
                has_deprecation_header = False
                if isinstance(responses, dict):
                    for resp in responses.values():
                        if isinstance(resp, dict):
                            hdrs = {str(k).lower() for k in resp.get("headers", {}).keys()}
                            if "deprecation" in hdrs and "sunset" in hdrs:
                                has_deprecation_header = True
                if not has_deprecation_header:
                    errors.append(f"{m.upper()} {path}: deprecated operation must document RFC 9745 'Deprecation' and RFC 8594 'Sunset' headers.")

    return {"check": "openapi_contract", "passed": len(errors) == 0, "errors": errors, "warnings": warnings}


def check_breaking_diff(old_spec: dict[str, Any], new_spec: dict[str, Any]) -> dict[str, Any]:
    breaking: list[str] = []
    additive: list[str] = []

    old_paths = old_spec.get("paths", {})
    new_paths = new_spec.get("paths", {})

    for path, old_item in old_paths.items():
        if path not in new_paths:
            breaking.append(f"REMOVED_PATH: '{path}' was removed without version isolation.")
            continue
        new_item = new_paths[path]
        for method, old_op in old_item.items():
            m = method.lower()
            if m not in {"get", "post", "put", "patch", "delete"}:
                continue
            if m not in new_item:
                breaking.append(f"REMOVED_OPERATION: {m.upper()} {path} removed.")
                continue
            new_op = new_item[m]

            # New required request fields break existing clients
            old_req = set(old_op.get("request_required_fields", []))
            new_req = set(new_op.get("request_required_fields", []))
            added_req = sorted(new_req - old_req)
            if added_req:
                breaking.append(f"NEW_REQUIRED_REQUEST_FIELD: {m.upper()} {path} added required field(s): {added_req}.")

            # Removed response fields break existing consumers
            old_resp = set(old_op.get("response_fields", []))
            new_resp = set(new_op.get("response_fields", []))
            removed_resp = sorted(old_resp - new_resp)
            if removed_resp:
                breaking.append(f"REMOVED_RESPONSE_FIELD: {m.upper()} {path} removed response field(s): {removed_resp}.")
            added_resp = sorted(new_resp - old_resp)
            if added_resp:
                additive.append(f"ADDITIVE_RESPONSE_FIELD: {m.upper()} {path} added optional field(s): {added_resp}.")

    return {
        "check": "breaking_diff",
        "passed": len(breaking) == 0,
        "breaking_changes": breaking,
        "additive_changes": additive,
    }


def run_self_test() -> dict[str, Any]:
    probes: list[tuple[str, bool]] = []

    # PRECISION-1: Clean RFC 9457 error response passes
    r1 = check_problem_json(
        {
            "content_type": "application/problem+json",
            "body": {
                "type": "https://api.example.com/problems/idempotency-conflict",
                "title": "Idempotency Key Payload Mismatch",
                "status": 422,
                "detail": "The Idempotency-Key was previously used with a different request payload.",
                "instance": "/api/v1/orders",
                "requestId": "req_01J9XYZ",
            },
        }
    )
    probes.append(("PRECISION-1: Clean RFC 9457 application/problem+json passes", r1["passed"] is True))

    # RECALL-1: Stack trace + SQL leak + wrong content-type rejected
    r2 = check_problem_json(
        {
            "content_type": "application/json",
            "body": {
                "status": 500,
                "detail": "PrismaClientKnownRequestError: SELECT * FROM users WHERE id = 1",
                "stack": "Error at handler (src/orders.ts:42:11)",
            },
        }
    )
    probes.append(("RECALL-1: Stack trace, SQL leak & wrong Content-Type rejected", r2["passed"] is False and len(r2["errors"]) >= 4))

    # PRECISION-2: Compliant OpenAPI 3.1 contract passes
    r3 = check_openapi_contract(
        {
            "openapi": "3.1.0",
            "paths": {
                "/api/v1/orders": {
                    "get": {
                        "operationId": "listOrders",
                        "x-collection": True,
                        "parameters": [{"name": "limit", "in": "query", "schema": {"type": "integer", "maximum": 50}}],
                    },
                    "post": {
                        "operationId": "createOrder",
                        "x-requires-idempotency": True,
                        "parameters": [{"name": "Idempotency-Key", "in": "header", "required": True}],
                    },
                },
                "/api/v1/legacy-orders": {
                    "get": {
                        "operationId": "listLegacyOrders",
                        "deprecated": True,
                        "responses": {"200": {"headers": {"Deprecation": {}, "Sunset": {}}}},
                    }
                },
            },
        }
    )
    probes.append(("PRECISION-2: Compliant OpenAPI 3.1 with bounded pagination, Idempotency-Key & Sunset passes", r3["passed"] is True))

    # RECALL-2: Missing Idempotency-Key, unbounded limit=500, missing Sunset on deprecated route rejected
    r4 = check_openapi_contract(
        {
            "openapi": "3.1.0",
            "paths": {
                "/api/v1/orders": {
                    "get": {
                        "operationId": "listOrders",
                        "x-collection": True,
                        "parameters": [{"name": "limit", "in": "query", "schema": {"type": "integer", "maximum": 500}}],
                    },
                    "post": {"operationId": "createOrder", "x-requires-idempotency": True, "parameters": []},
                },
                "/api/v1/legacy": {"get": {"deprecated": True, "responses": {"200": {}}}},
            },
        }
    )
    probes.append(("RECALL-2: Unbounded pagination, missing Idempotency-Key & missing Sunset rejected", r4["passed"] is False and len(r4["errors"]) >= 4))

    # PRECISION-3: Additive-only v1 -> v2 diff passes
    r5 = check_breaking_diff(
        {"paths": {"/orders": {"post": {"request_required_fields": ["sku"], "response_fields": ["id", "status"]}}}},
        {"paths": {"/orders": {"post": {"request_required_fields": ["sku"], "response_fields": ["id", "status", "currency"]}}}},
    )
    probes.append(("PRECISION-3: Additive-only evolution diff passes", r5["passed"] is True and len(r5["additive_changes"]) == 1))

    # RECALL-3: New required request field & removed response field caught as breaking
    r6 = check_breaking_diff(
        {"paths": {"/orders": {"post": {"request_required_fields": ["sku"], "response_fields": ["id", "status"]}}}},
        {"paths": {"/orders": {"post": {"request_required_fields": ["sku", "tax_id"], "response_fields": ["id"]}}}},
    )
    probes.append(("RECALL-3: New required request field & removed response field flagged as breaking", r6["passed"] is False and len(r6["breaking_changes"]) == 2))

    # RECALL-4: Removed path caught as breaking
    r7 = check_breaking_diff(
        {"paths": {"/v1/invoices": {"get": {}}}},
        {"paths": {"/v2/invoices": {"get": {}}}},
    )
    probes.append(("RECALL-4: Removed endpoint path flagged as breaking", r7["passed"] is False and any("REMOVED_PATH" in b for b in r7["breaking_changes"])))

    passed = sum(1 for _, ok in probes if ok)
    return {
        "tool": "api_contract_verifier.py",
        "total_probes": len(probes),
        "passed": passed,
        "failed": len(probes) - passed,
        "all_passed": passed == len(probes),
        "results": [{"probe": n, "passed": ok} for n, ok in probes],
    }


def _load_json(path_str: str) -> dict[str, Any]:
    raw = json.loads(Path(path_str).read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"Expected JSON object in {path_str}")
    return raw


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Offline API Contract, RFC 9457 & Breaking-Diff Verifier")
    parser.add_argument("--self-test", action="store_true", help="Run built-in precision & recall probes")
    parser.add_argument("--check-problem-json", metavar="PATH", help="Validate RFC 9457 error envelope JSON")
    parser.add_argument("--check-openapi-contract", metavar="PATH", help="Validate OpenAPI 3.x contract hygiene JSON")
    parser.add_argument("--check-breaking-diff", nargs=2, metavar=("OLD_PATH", "NEW_PATH"), help="Check breaking contract diff")
    args = parser.parse_args(argv)

    if args.self_test:
        res = run_self_test()
        print(json.dumps(res, indent=2))
        return 0 if res["all_passed"] else 1
    if args.check_problem_json:
        res = check_problem_json(_load_json(args.check_problem_json))
        print(json.dumps(res, indent=2))
        return 0 if res["passed"] else 1
    if args.check_openapi_contract:
        res = check_openapi_contract(_load_json(args.check_openapi_contract))
        print(json.dumps(res, indent=2))
        return 0 if res["passed"] else 1
    if args.check_breaking_diff:
        res = check_breaking_diff(_load_json(args.check_breaking_diff[0]), _load_json(args.check_breaking_diff[1]))
        print(json.dumps(res, indent=2))
        return 0 if res["passed"] else 1

    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
