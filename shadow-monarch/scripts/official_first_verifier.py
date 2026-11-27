#!/usr/bin/env python3
"""
Official-First Project Initialization, Dependency Verification & SSO SDK Gate (official_first_verifier.py)

Deterministic fail-closed verifier enforcing:
1. Official CLI generator usage for new projects (saving output tokens over from-scratch boilerplate)
2. 8-field Technology & Dependency Decision Record completeness
3. Non-destructive dependency trust & version pinning checks (no blind `latest` in prod/regulated)
4. Reuse-before-rebuild discipline & explicit approval on architecture/SDK replacement
5. Auth/SSO SDK preservation (including `ridhuan-sso` / `file:../sdk/sso-client`) & verified claims
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from shadow_input import run_checked_cli, strict_bool

REQUIRED_DECISION_FIELDS = (
    "technology",
    "source",
    "version",
    "trust_status",
    "compatibility",
    "existing_alternative",
    "decision",
    "approval",
)
VALID_TRUST_STATUSES = {"Verified", "Unverified", "Blocked"}
VALID_DECISIONS = {"Reuse", "Scaffold", "Install", "Custom"}
VALID_APPROVALS = {"Required", "Not required"}
FLOATING_VERSION_RE = re.compile(r"^(?:latest|\*|next|canary|main)$", re.IGNORECASE)


def verify_decision_record(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate 8-field Decision Record and enforce §1-§4 Official-First rules."""
    errors: list[str] = []
    codes: list[str] = []

    record = payload.get("decision_record", payload)
    task_class = str(payload.get("task_class") or "existing_project_enhancement").strip().lower()
    env = str(payload.get("environment") or "development").strip().lower()

    # 1. Check all 8 mandatory fields
    missing = [f for f in REQUIRED_DECISION_FIELDS if not str(record.get(f) or "").strip()]
    if missing:
        codes.append("BLOCKED_MISSING_DECISION_FIELDS")
        errors.append(f"Missing required 8-field Decision Record keys: {missing}.")

    trust_status = str(record.get("trust_status") or "").strip()
    decision = str(record.get("decision") or "").strip()
    approval = str(record.get("approval") or "").strip()
    version = str(record.get("version") or "").strip()

    if trust_status and trust_status not in VALID_TRUST_STATUSES:
        codes.append("BLOCKED_MISSING_DECISION_FIELDS")
        errors.append(f"Invalid `trust_status`: '{trust_status}' (must be Verified, Unverified, or Blocked).")
    if decision and decision not in VALID_DECISIONS:
        codes.append("BLOCKED_MISSING_DECISION_FIELDS")
        errors.append(f"Invalid `decision`: '{decision}' (must be Reuse, Scaffold, Install, or Custom).")
    if approval and approval not in VALID_APPROVALS:
        codes.append("BLOCKED_MISSING_DECISION_FIELDS")
        errors.append(f"Invalid `approval`: '{approval}' (must be Required or Not required).")

    # 2. Failure Condition: manually recreating framework scaffold when official generator exists
    if task_class == "new_project" and strict_bool(payload.get("official_generator_available", False), "official_generator_available"):
        used_gen = strict_bool(payload.get("used_official_generator", False), "used_official_generator")
        justification = payload.get("official_generator_unsuitable_justification")
        justified = isinstance(justification, str) and bool(justification.strip())
        if (decision == "Custom" or not used_gen) and not justified:
            codes.append("BLOCKED_MANUAL_SCAFFOLD_TOKEN_WASTE")
            errors.append(
                "New project must invoke verified official CLI generator instead of manual from-scratch boilerplate."
            )

    # 3. Failure Condition: unverified dependency / install-to-inspect
    if strict_bool(payload.get("installed_only_to_inspect", False), "installed_only_to_inspect"):
        codes.append("BLOCKED_UNVERIFIED_DEPENDENCY")
        errors.append("Do not install an unverified package merely to inspect it; use `npm view` / registry metadata first.")

    if decision == "Install":
        publisher_verified = strict_bool(payload.get("publisher_verified", False), "publisher_verified")
        repository_verified = strict_bool(payload.get("repository_verified", False), "repository_verified")
        if trust_status in {"Unverified", "Blocked"} or not publisher_verified or not repository_verified:
            codes.append("BLOCKED_UNVERIFIED_DEPENDENCY")
            errors.append("Cannot adopt or treat an unverified package as production-ready (`publisher_verified`/`repository_verified`/`trust_status` failed).")

    # 4. Version pinning in regulated / production / staging environments
    if version and FLOATING_VERSION_RE.match(version) and env in {"production", "staging", "regulated"}:
        codes.append("BLOCKED_UNPINNED_LATEST_VERSION")
        errors.append(f"Floating version `{version}` is prohibited in `{env}` environments; resolve and pin an approved version.")

    # 5. Reuse before rebuild unless insecure/obsolete/incompatible or justified
    if decision == "Custom":
        if strict_bool(payload.get("existing_trusted_sdk_available", False), "existing_trusted_sdk_available") and not strict_bool(payload.get("existing_sdk_insecure_or_incompatible", False), "existing_sdk_insecure_or_incompatible"):
            if not str(payload.get("custom_rationale") or "").strip():
                codes.append("BLOCKED_UNJUSTIFIED_CUSTOM_REBUILD")
                errors.append("Custom implementation chosen despite available compatible trusted SDK without technical rationale.")
        elif not str(payload.get("custom_rationale") or "").strip():
            codes.append("BLOCKED_UNJUSTIFIED_CUSTOM_REBUILD")
            errors.append("Custom implementation requires documented rationale explaining why official options are unsuitable.")

    # 6. Approval required for major deviation / SDK replacement / infra additions
    deviation_flags = (
        "replaces_auth_or_sso_sdk",
        "introduces_new_framework",
        "changes_package_manager",
        "adds_unrequested_infrastructure",
        "departs_from_existing_conventions",
    )
    needs_approval = any([strict_bool(payload.get(field, False), field) for field in deviation_flags])
    user_approval = strict_bool(payload.get("user_approval_granted", False), "user_approval_granted")
    if needs_approval and not user_approval:
        codes.append("BLOCKED_UNAUTHORIZED_SDK_OR_ARCH_REPLACEMENT")
        errors.append("Material architecture/SDK/framework/infrastructure deviation requires explicit user approval (`user_approval_granted: true`).")

    return {
        "gate": "official-first-verifier v1.0",
        "status": "PASS" if not errors else "BLOCKED",
        "valid": len(errors) == 0,
        "codes": sorted(set(codes)),
        "errors": errors,
    }


def verify_auth_sdk_policy(spec: dict[str, Any]) -> dict[str, Any]:
    """Enforce Special Rule: Authentication, SSO, and `ridhuan-sso` (`file:../sdk/sso-client`)."""
    errors: list[str] = []
    codes: list[str] = []

    sdk_source = str(spec.get("existing_sdk_source") or "").strip()
    target_source = str(spec.get("proposed_source") or sdk_source).strip()
    custom_login = strict_bool(spec.get("creates_custom_login_replacement", False), "creates_custom_login_replacement")
    user_approval = strict_bool(spec.get("user_approval_granted", False), "user_approval_granted")
    trusts_fe_username = strict_bool(spec.get("trusts_frontend_username_without_verified_claims", False), "trusts_frontend_username_without_verified_claims")
    verified_claims = strict_bool(spec.get("verified_authenticated_claims", False), "verified_authenticated_claims")
    is_local_sso = ("sso-client" in sdk_source) or ("ridhuan-sso" in str(spec.get("sdk_name") or ""))

    publisher_verified = strict_bool(spec.get("publisher_ownership_verified", False), "publisher_ownership_verified")
    if is_local_sso and target_source and target_source != sdk_source:
        if not publisher_verified:
            codes.append("BLOCKED_UNVERIFIED_NPM_LOOKALIKE_SUBSTITUTION")
            errors.append(
                f"Cannot replace `{sdk_source}` with `{target_source}` without verified publisher ownership."
            )
        if not user_approval:
            codes.append("BLOCKED_UNAUTHORIZED_SDK_OR_ARCH_REPLACEMENT")
            errors.append("Replacing an existing internal/local SSO SDK requires explicit user approval.")

    if custom_login and not user_approval:
        codes.append("BLOCKED_UNAUTHORIZED_SDK_OR_ARCH_REPLACEMENT")
        errors.append("Creating a custom login replacement when an existing SSO SDK exists requires explicit user approval.")

    if trusts_fe_username or not verified_claims:
        codes.append("BLOCKED_FRONTEND_USERNAME_TRUSTED_AS_AUTH")
        errors.append("Never trust frontend-supplied `username` as authentication proof; require `verified_authenticated_claims: true`.")

    return {
        "gate": "official-first-auth-sso-verifier v1.0",
        "status": "PASS" if not errors else "BLOCKED",
        "valid": len(errors) == 0,
        "codes": sorted(set(codes)),
        "errors": errors,
    }


def run_self_test() -> dict[str, Any]:
    """Execute 8 negative probes (all failure conditions) + 4 positive workflow probes."""
    probes: list[dict[str, Any]] = []

    def _base_valid_record(**overrides: Any) -> dict[str, Any]:
        rec = {
            "technology": "vite-react-ts",
            "source": "https://vite.dev/guide/",
            "version": "5.4.10",
            "trust_status": "Verified",
            "compatibility": "Node 20 LTS / TypeScript 5.x strict",
            "existing_alternative": "None (new project)",
            "decision": "Scaffold",
            "approval": "Not required",
        }
        rec.update(overrides)
        return rec

    # OF-NEG-01: Manual from-scratch scaffold when official CLI exists must block
    r1 = verify_decision_record({
        "task_class": "new_project",
        "official_generator_available": True,
        "used_official_generator": False,
        "decision_record": _base_valid_record(decision="Custom"),
    })
    probes.append({"probe": "OF-NEG-01: Manual boilerplate on new project blocked", "passed": r1["status"] == "BLOCKED" and "BLOCKED_MANUAL_SCAFFOLD_TOKEN_WASTE" in r1["codes"], "codes": r1["codes"]})

    # OF-NEG-02: Adopting unverified registry package by name must block
    r2 = verify_decision_record({
        "task_class": "sdk_integration",
        "publisher_verified": False,
        "repository_verified": False,
        "decision_record": _base_valid_record(technology="ridhuan-sso-helper", trust_status="Unverified", decision="Install", version="1.0.0"),
    })
    probes.append({"probe": "OF-NEG-02: Unverified registry dependency blocked", "passed": r2["status"] == "BLOCKED" and "BLOCKED_UNVERIFIED_DEPENDENCY" in r2["codes"], "codes": r2["codes"]})

    # OF-NEG-03: Floating `latest` version in production/regulated environment must block
    r3 = verify_decision_record({
        "task_class": "new_project",
        "environment": "production",
        "official_generator_available": True,
        "used_official_generator": True,
        "decision_record": _base_valid_record(version="latest"),
    })
    probes.append({"probe": "OF-NEG-03: Floating `latest` blocked in production", "passed": r3["status"] == "BLOCKED" and "BLOCKED_UNPINNED_LATEST_VERSION" in r3["codes"], "codes": r3["codes"]})

    # OF-NEG-04: Installing unverified package only to inspect must block
    r4 = verify_decision_record({
        "task_class": "sdk_integration",
        "installed_only_to_inspect": True,
        "decision_record": _base_valid_record(decision="Install", trust_status="Verified"),
    })
    probes.append({"probe": "OF-NEG-04: Install-only-to-inspect blocked", "passed": r4["status"] == "BLOCKED" and "BLOCKED_UNVERIFIED_DEPENDENCY" in r4["codes"], "codes": r4["codes"]})

    # OF-NEG-05: Custom rebuild when existing compatible trusted SDK is available without rationale
    r5 = verify_decision_record({
        "task_class": "existing_project_enhancement",
        "existing_trusted_sdk_available": True,
        "existing_sdk_insecure_or_incompatible": False,
        "decision_record": _base_valid_record(decision="Custom", existing_alternative="file:../sdk/sso-client"),
    })
    probes.append({"probe": "OF-NEG-05: Unjustified custom rebuild when SDK exists blocked", "passed": r5["status"] == "BLOCKED" and "BLOCKED_UNJUSTIFIED_CUSTOM_REBUILD" in r5["codes"], "codes": r5["codes"]})

    # OF-NEG-06: Replacing `file:../sdk/sso-client` (`ridhuan-sso`) with unverified npm lookalike without approval
    r6 = verify_auth_sdk_policy({
        "sdk_name": "ridhuan-sso",
        "existing_sdk_source": "file:../sdk/sso-client",
        "proposed_source": "npm:ridhuan-sso@1.0.2",
        "publisher_ownership_verified": False,
        "user_approval_granted": False,
        "verified_authenticated_claims": True,
    })
    probes.append({"probe": "OF-NEG-06: Replacing `ridhuan-sso` with unverified npm package blocked", "passed": r6["status"] == "BLOCKED" and "BLOCKED_UNVERIFIED_NPM_LOOKALIKE_SUBSTITUTION" in r6["codes"], "codes": r6["codes"]})

    # OF-NEG-07: Trusting frontend-supplied username as auth proof without verified claims
    r7 = verify_auth_sdk_policy({
        "sdk_name": "ridhuan-sso",
        "existing_sdk_source": "file:../sdk/sso-client",
        "trusts_frontend_username_without_verified_claims": True,
        "verified_authenticated_claims": False,
    })
    probes.append({"probe": "OF-NEG-07: Frontend `username` trusted without verified claims blocked", "passed": r7["status"] == "BLOCKED" and "BLOCKED_FRONTEND_USERNAME_TRUSTED_AS_AUTH" in r7["codes"], "codes": r7["codes"]})

    # OF-NEG-08: Missing fields in 8-field Decision Record must block
    r8 = verify_decision_record({
        "task_class": "sdk_integration",
        "decision_record": {"technology": "zod", "decision": "Install"},
    })
    probes.append({"probe": "OF-NEG-08: Incomplete Decision Record blocked", "passed": r8["status"] == "BLOCKED" and "BLOCKED_MISSING_DECISION_FIELDS" in r8["codes"], "codes": r8["codes"]})

    # OF-POS-01: Official Vite CLI generator on new project with pinned version & full 8-field record passes
    p1 = verify_decision_record({
        "task_class": "new_project",
        "environment": "production",
        "official_generator_available": True,
        "used_official_generator": True,
        "decision_record": _base_valid_record(),
    })
    probes.append({"probe": "OF-POS-01: Official CLI scaffold with pinned version passes", "passed": p1["valid"]})

    # OF-POS-02: Verified mature dependency install with complete Decision Record passes
    p2 = verify_decision_record({
        "task_class": "sdk_integration",
        "environment": "staging",
        "publisher_verified": True,
        "repository_verified": True,
        "decision_record": _base_valid_record(technology="zod", source="https://zod.dev", version="3.24.2", decision="Install", existing_alternative="None"),
    })
    probes.append({"probe": "OF-POS-02: Verified mature dependency install passes", "passed": p2["valid"]})

    # OF-POS-03: Preserving local `ridhuan-sso` (`file:../sdk/sso-client`) with verified claims passes
    p3 = verify_auth_sdk_policy({
        "sdk_name": "ridhuan-sso",
        "existing_sdk_source": "file:../sdk/sso-client",
        "proposed_source": "file:../sdk/sso-client",
        "creates_custom_login_replacement": False,
        "trusts_frontend_username_without_verified_claims": False,
        "verified_authenticated_claims": True,
    })
    probes.append({"probe": "OF-POS-03: Preserving local `ridhuan-sso` SDK with verified claims passes", "passed": p3["valid"]})

    # OF-POS-04: Small custom implementation when official option unsuitable & rationale documented passes
    p4 = verify_decision_record({
        "task_class": "existing_project_enhancement",
        "existing_trusted_sdk_available": False,
        "custom_rationale": "Only requires a 12-line HMAC timestamp header guard already standardized across sibling controllers.",
        "decision_record": _base_valid_record(technology="hmac-timestamp-guard", source="internal codebase precedent", version="1.0.0", decision="Custom", existing_alternative="No lightweight standalone official package"),
    })
    probes.append({"probe": "OF-POS-04: Justified custom implementation passes", "passed": p4["valid"]})

    passed = sum(1 for pr in probes if pr["passed"])
    return {
        "tool": "official_first_verifier.py",
        "total_probes": len(probes),
        "passed": passed,
        "failed": len(probes) - passed,
        "all_passed": passed == len(probes),
        "results": probes,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Shadow Monarch Official-First & Dependency Verification Gate")
    parser.add_argument("--verify-decision", default=None, help="Path to JSON file containing task_class, flags, and 8-field decision_record")
    parser.add_argument("--check-auth-sdk", default=None, help="Path to JSON file checking existing SSO/Auth SDK preservation rules")
    parser.add_argument("--out", default=None, help="Optional output file path for JSON report")
    parser.add_argument("--self-test", action="store_true", help="Run 8 failure-condition probes + 4 positive workflow probes")
    args = parser.parse_args()

    result: dict[str, Any]
    exit_code = 0

    if args.self_test:
        result = run_self_test()
        exit_code = 0 if result["all_passed"] else 1
    elif args.verify_decision:
        payload = json.loads(Path(args.verify_decision).read_text(encoding="utf-8-sig"))
        result = verify_decision_record(payload)
        exit_code = 0 if result["valid"] else 2
    elif args.check_auth_sdk:
        payload = json.loads(Path(args.check_auth_sdk).read_text(encoding="utf-8-sig"))
        result = verify_auth_sdk_policy(payload)
        exit_code = 0 if result["valid"] else 2
    else:
        parser.print_help()
        return 0

    rendered = json.dumps(result, indent=2, ensure_ascii=False)
    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return exit_code


if __name__ == "__main__":
    sys.exit(run_checked_cli(main))
