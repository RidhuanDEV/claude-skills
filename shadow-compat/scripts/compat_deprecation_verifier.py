#!/usr/bin/env python3
"""Deterministic API compatibility, RFC 9745/8594 deprecation & semantic diff verifier for shadow-compat.

Audits:
  1. RFC 9745 `Deprecation: @<unix_sec>` header format (rejects obsolete draft `Deprecation: true`)
  2. RFC 8594 `Sunset: <IMF-fixdate>` header format & temporal invariant (`Sunset >= Deprecation`)
  3. Migration `Link` header (`rel="deprecation"` / `rel="alternate"`) & post-sunset `410 Gone` (not `404`)
  4. Breaking API schema diffs (removed response field, added required request field, type mutation,
     non-nullable -> nullable flip on response, or strict `additionalProperties: false` tightening)
Zero external dependencies (Python stdlib only).
"""

from __future__ import annotations

import argparse
import email.utils
import json
import re
import sys
from pathlib import Path
from typing import Any

RFC9745_DEP_RE = re.compile(r"^@(\d{9,12})$")


def check_compat_spec(spec: Any) -> list[dict[str, str]]:
    """Audit deprecation headers and API contract diff rules."""
    violations: list[dict[str, str]] = []
    if not isinstance(spec, dict) or not spec:
        return [{"code": "EMPTY_SPEC", "detail": "Compatibility spec must be a non-empty JSON object."}]

    # 1. RFC 9745 / RFC 8594 deprecation policy check
    dep = spec.get("deprecation")
    if isinstance(dep, dict):
        dep_hdr = str(dep.get("Deprecation", "")).strip()
        sunset_hdr = str(dep.get("Sunset", "")).strip()
        link_hdr = str(dep.get("Link", "")).strip()
        dep_ts: int | None = None

        m = RFC9745_DEP_RE.match(dep_hdr)
        if not m:
            violations.append({
                "code": "INVALID_RFC9745_DEPRECATION",
                "detail": f"`Deprecation` header (`{dep_hdr}`) must use RFC 9745 `@<unix_seconds>` syntax (never draft `true`).",
            })
        else:
            dep_ts = int(m.group(1))

        if sunset_hdr:
            try:
                sunset_dt = email.utils.parsedate_to_datetime(sunset_hdr)
                if sunset_dt.tzinfo is None:
                    raise ValueError("Missing GMT/UTC timezone")
                sunset_ts = int(sunset_dt.timestamp())
                if dep_ts is not None and sunset_ts < dep_ts:
                    violations.append({
                        "code": "SUNSET_BEFORE_DEPRECATION",
                        "detail": "RFC 8594 `Sunset` timestamp MUST NOT precede RFC 9745 `Deprecation` timestamp.",
                    })
            except Exception:
                violations.append({
                    "code": "INVALID_RFC8594_SUNSET",
                    "detail": f"`Sunset` header (`{sunset_hdr}`) must be a valid IMF-fixdate in GMT (e.g. `Wed, 31 Dec 2026 23:59:59 GMT`).",
                })
        else:
            violations.append({
                "code": "MISSING_SUNSET_HEADER",
                "detail": "Deprecated endpoint should declare an RFC 8594 `Sunset` header.",
            })

        if 'rel="deprecation"' not in link_hdr and 'rel="alternate"' not in link_hdr:
            violations.append({
                "code": "MISSING_MIGRATION_LINK",
                "detail": "Deprecated endpoint must include `Link` header with `rel=\"deprecation\"` or `rel=\"alternate\"`.",
            })

        retired_status = dep.get("post_sunset_status")
        if retired_status is not None and int(retired_status) != 410:
            violations.append({
                "code": "WRONG_POST_SUNSET_STATUS",
                "detail": f"Post-sunset retired endpoint returned `{retired_status}`; emit HTTP `410 Gone` (not `404`).",
            })

    # 2. Contract diff breaking-change check
    diff = spec.get("contract_diff")
    if isinstance(diff, dict):
        old_res = diff.get("old_response_fields", {})
        new_res = diff.get("new_response_fields", {})
        for field, old_meta in old_res.items():
            if field not in new_res:
                violations.append({
                    "code": "BREAKING_RESPONSE_FIELD_REMOVED",
                    "detail": f"Response field `{field}` was removed in-place without major version bump or deprecation drain.",
                })
                continue
            new_meta = new_res[field]
            if old_meta.get("type") != new_meta.get("type"):
                violations.append({
                    "code": "BREAKING_RESPONSE_TYPE_CHANGED",
                    "detail": f"Response field `{field}` changed type `{old_meta.get('type')}` -> `{new_meta.get('type')}`.",
                })
            if not old_meta.get("nullable", False) and new_meta.get("nullable", False):
                violations.append({
                    "code": "BREAKING_RESPONSE_BECAME_NULLABLE",
                    "detail": f"Response field `{field}` became nullable (`null` breaks strict existing mobile/web decoders).",
                })

        old_req = diff.get("old_request_fields", {})
        new_req = diff.get("new_request_fields", {})
        for field, new_meta in new_req.items():
            was_required = bool(old_req.get(field, {}).get("required", False))
            now_required = bool(new_meta.get("required", False))
            if now_required and not was_required:
                violations.append({
                    "code": "BREAKING_NEW_REQUIRED_REQUEST_FIELD",
                    "detail": f"Request field `{field}` became required without server default (breaks existing callers).",
                })

        if bool(diff.get("added_additional_properties_false", False)):
            violations.append({
                "code": "BREAKING_STRICT_SCHEMA_TIGHTENING",
                "detail": "Enabling `additionalProperties: false` breaks forward-compatible tolerant readers/clients.",
            })

    return violations


def run_self_test() -> dict[str, Any]:
    probes: list[tuple[str, bool]] = []

    # PRECISION-1: Valid RFC 9745/8594 headers + additive non-breaking schema change pass
    v = check_compat_spec({
        "deprecation": {
            "Deprecation": "@1767225600",
            "Sunset": "Thu, 31 Dec 2026 23:59:59 GMT",
            "Link": '<https://api.example.com/v2/orders>; rel="alternate", <https://docs.example.com/migrate>; rel="deprecation"',
            "post_sunset_status": 410,
        },
        "contract_diff": {
            "old_response_fields": {"id": {"type": "string", "nullable": False}},
            "new_response_fields": {
                "id": {"type": "string", "nullable": False},
                "loyalty_points": {"type": "number", "nullable": True},
            },
            "old_request_fields": {"amount": {"required": True}},
            "new_request_fields": {"amount": {"required": True}, "note": {"required": False}},
        },
    })
    probes.append(("PRECISION-1: RFC 9745 @unix, RFC 8594 Sunset, 410 Gone & additive fields pass", len(v) == 0))

    # RECALL-1: Draft `Deprecation: true` and `404` post-sunset rejected
    v = check_compat_spec({
        "deprecation": {
            "Deprecation": "true",
            "Sunset": "Thu, 31 Dec 2026 23:59:59 GMT",
            "Link": "",
            "post_sunset_status": 404,
        }
    })
    codes = {x["code"] for x in v}
    probes.append((
        "RECALL-1: Rejects draft `Deprecation: true`, missing Link, and 404 post-sunset",
        {"INVALID_RFC9745_DEPRECATION", "MISSING_MIGRATION_LINK", "WRONG_POST_SUNSET_STATUS"}.issubset(codes),
    ))

    # RECALL-2: Sunset earlier than Deprecation rejected
    v = check_compat_spec({
        "deprecation": {
            "Deprecation": "@1798761600",  # 2027-01-01
            "Sunset": "Wed, 31 Dec 2025 23:59:59 GMT",
            "Link": '<https://docs.example.com>; rel="deprecation"',
        }
    })
    codes = {x["code"] for x in v}
    probes.append(("RECALL-2: Rejects Sunset preceding Deprecation timestamp", "SUNSET_BEFORE_DEPRECATION" in codes))

    # RECALL-3: Removed response field & type mutation rejected
    v = check_compat_spec({
        "contract_diff": {
            "old_response_fields": {"code": {"type": "string"}, "total": {"type": "number", "nullable": False}},
            "new_response_fields": {"total": {"type": "string", "nullable": False}},
        }
    })
    codes = {x["code"] for x in v}
    probes.append((
        "RECALL-3: Rejects removed response field and field type mutation",
        {"BREAKING_RESPONSE_FIELD_REMOVED", "BREAKING_RESPONSE_TYPE_CHANGED"}.issubset(codes),
    ))

    # RECALL-4: Non-nullable -> nullable response flip & newly required request field rejected
    v = check_compat_spec({
        "contract_diff": {
            "old_response_fields": {"total": {"type": "number", "nullable": False}},
            "new_response_fields": {"total": {"type": "number", "nullable": True}},
            "old_request_fields": {"amount": {"required": True}},
            "new_request_fields": {"amount": {"required": True}, "tax_id": {"required": True}},
        }
    })
    codes = {x["code"] for x in v}
    probes.append((
        "RECALL-4: Rejects response becoming nullable & new required request field",
        {"BREAKING_RESPONSE_BECAME_NULLABLE", "BREAKING_NEW_REQUIRED_REQUEST_FIELD"}.issubset(codes),
    ))

    # RECALL-5: Strict `additionalProperties: false` schema tightening rejected
    v = check_compat_spec({"contract_diff": {"added_additional_properties_false": True}})
    probes.append(("RECALL-5: Rejects strict additionalProperties: false tightening", any(x["code"] == "BREAKING_STRICT_SCHEMA_TIGHTENING" for x in v)))

    # BOUNDARY-1: Empty spec rejected cleanly
    v = check_compat_spec({})
    probes.append(("BOUNDARY-1: Rejects empty compatibility spec gracefully", len(v) == 1 and v[0]["code"] == "EMPTY_SPEC"))

    passed = sum(1 for _, ok in probes if ok)
    return {
        "tool": "compat_deprecation_verifier.py",
        "total_probes": len(probes),
        "passed": passed,
        "failed": len(probes) - passed,
        "all_passed": passed == len(probes),
        "results": [{"probe": name, "passed": ok} for name, ok in probes],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify RFC 9745/8594 deprecation headers and backward-compatible API diffs.")
    parser.add_argument("--self-test", action="store_true", help="Run built-in precision/recall falsification probes.")
    parser.add_argument("--check-compat", type=Path, help="Path to JSON compatibility & deprecation spec.")
    args = parser.parse_args(argv)

    if args.self_test:
        report = run_self_test()
        print(json.dumps(report, indent=2))
        return 0 if report["all_passed"] else 1

    if not args.check_compat:
        parser.print_help()
        return 2

    data = json.loads(args.check_compat.read_text(encoding="utf-8"))
    violations = check_compat_spec(data)
    output = {"status": "PASS" if not violations else "FAIL", "violation_count": len(violations), "violations": violations}
    print(json.dumps(output, indent=2))
    return 0 if not violations else 1


if __name__ == "__main__":
    sys.exit(main())
