#!/usr/bin/env python3
"""Deterministic Analytics, Tracking Plan, Experimentation & DSAR Verifier (L0/L1 offline CLI).

Zero third-party dependencies (Python 3 stdlib only).
Validates:
  - Event taxonomy, repeatable occurrence-unique event_id, and PII scrubbing (--check-event)
  - Experiment SRM (chi-square goodness-of-fit), Assignment vs Exposure separation,
    Power/MDE, Two-Proportion Z-test, Delta Method for ratio metrics, CUPED pre-experiment
    covariate validity, and guardrail override verdict (--check-experiment)
  - End-to-end DSAR deletion coverage across BOTH warehouse and third-party vendors (--check-dsar-plan)
  - Built-in precision & recall self-test probes (--self-test)
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "shadow-monarch" / "scripts"))
from shadow_input import InvalidInput, run_checked_cli, strict_bool

EVENT_NAME_RE = re.compile(r"^[A-Z][a-zA-Z0-9]*_[A-Z][a-zA-Z0-9]*$")
ISO_TS_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$")
FORBIDDEN_PII_KEYS = {
    "email",
    "email_address",
    "phone",
    "phone_number",
    "mobile",
    "nik",
    "ktp",
    "npwp",
    "ssn",
    "password",
    "passwd",
    "token",
    "access_token",
    "refresh_token",
    "secret",
    "credit_card",
    "card_number",
    "cvv",
    "full_address",
    "street_address",
    "home_address",
}


def _normal_cdf(z: float) -> float:
    return 0.5 * math.erfc(-z / math.sqrt(2.0))


def _normal_two_sided_p(z: float) -> float:
    return math.erfc(abs(z) / math.sqrt(2.0))


def _chi2_upper_tail_p(chi2: float, df: int) -> float:
    """Exact upper-tail p-value Q(df/2, chi2/2) for chi-square distribution."""
    if chi2 <= 0.0:
        return 1.0
    if df <= 0:
        raise ValueError("Degrees of freedom must be >= 1")
    if df == 1:
        return math.erfc(math.sqrt(chi2 / 2.0))
    if df == 2:
        return math.exp(-chi2 / 2.0)

    a = df / 2.0
    x = chi2 / 2.0
    # Regularized upper incomplete gamma Q(a, x) via series (x < a + 1) or Lentz CF (x >= a + 1)
    if x < a + 1.0:
        ap = a
        term = 1.0 / a
        total = term
        for _ in range(300):
            ap += 1.0
            term *= x / ap
            total += term
            if abs(term) < abs(total) * 1e-13:
                break
        p_lower = total * math.exp(-x + a * math.log(x) - math.lgamma(a))
        return max(0.0, min(1.0, 1.0 - p_lower))

    b = x + 1.0 - a
    c = 1.0 / 1e-30
    d = 1.0 / b
    h = d
    for i in range(1, 300):
        an = -i * (i - a)
        b += 2.0
        d = an * d + b
        if abs(d) < 1e-30:
            d = 1e-30
        c = b + an / c
        if abs(c) < 1e-30:
            c = 1e-30
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < 1e-13:
            break
    q_upper = math.exp(-x + a * math.log(x) - math.lgamma(a)) * h
    return max(0.0, min(1.0, q_upper))


def _find_pii_keys(obj: Any, prefix: str = "") -> list[str]:
    hits: list[str] = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            key_lower = str(k).strip().lower()
            full_path = f"{prefix}.{k}" if prefix else str(k)
            if key_lower in FORBIDDEN_PII_KEYS:
                hits.append(full_path)
            hits.extend(_find_pii_keys(v, full_path))
    elif isinstance(obj, list):
        for idx, item in enumerate(obj):
            hits.extend(_find_pii_keys(item, f"{prefix}[{idx}]"))
    return hits


def check_event(payload: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []

    event_name = payload.get("event")
    if not isinstance(event_name, str) or not EVENT_NAME_RE.match(event_name):
        errors.append(
            f"Event name '{event_name}' must follow Object_Action Pascal_Snake convention (e.g., Checkout_Started)."
        )

    event_id = payload.get("event_id")
    if not isinstance(event_id, str) or len(event_id.strip()) < 8:
        errors.append("Missing or weak 'event_id' (must be >= 8 chars, unique per occurrence and stable across retries).")

    schema_version = payload.get("schema_version")
    if not (isinstance(schema_version, int) and schema_version >= 1) and not (
        isinstance(schema_version, str) and bool(re.match(r"^\d+\.\d+\.\d+$", schema_version))
    ):
        errors.append("Missing or invalid 'schema_version' (require integer >= 1 or semver 'X.Y.Z').")

    ts = payload.get("timestamp")
    if not isinstance(ts, str) or not ISO_TS_RE.match(ts):
        errors.append("Missing or invalid ISO-8601 UTC 'timestamp'.")

    # Mandatory correction #3: repeatable events cannot use static entity hashes
    repeatable = strict_bool(payload.get("repeatable", True), "repeatable")
    id_strategy = str(payload.get("event_id_strategy", "occurrence_uuid")).strip().lower()
    if repeatable and id_strategy in {"static_entity_hash", "entity_transition_hash", "deterministic_entity_only"}:
        errors.append(
            "Repeatable event cannot use static entity-only event_id hash (would silently drop legitimate repeat occurrences). "
            "Generate a unique per-occurrence ID (e.g., UUIDv7) at emission time and reuse that exact ID across retries."
        )

    properties = payload.get("properties", {})
    user_traits = payload.get("user_traits", {})
    pii_hits = _find_pii_keys(properties, "properties") + _find_pii_keys(user_traits, "user_traits")
    if pii_hits:
        errors.append(f"Raw PII keys detected in analytics payload: {', '.join(pii_hits)}.")

    if not payload.get("anonymous_id") and not payload.get("user_id"):
        errors.append("Event must carry at least one identity key ('anonymous_id' or 'user_id').")

    if not strict_bool(payload.get("consent_analytics", True), "consent_analytics"):
        errors.append("Event emitted while 'consent_analytics' is explicitly false (violates consent gate).")

    return {
        "check": "event_contract",
        "passed": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
    }


def _required_sample_per_variant_proportion(
    p0: float,
    mde_relative: float,
    alpha: float = 0.05,
    power: float = 0.80,
) -> int:
    if not (0.0 < p0 < 1.0) or mde_relative <= 0.0:
        raise ValueError("baseline_rate must be in (0, 1) and mde_relative > 0")
    p1 = min(0.999999, p0 * (1.0 + mde_relative))
    # Standard normal quantiles for common alpha/power defaults
    z_alpha = 1.959963984540054 if abs(alpha - 0.05) < 1e-9 else 2.5758293035489004
    z_beta = 0.8416212335729143 if abs(power - 0.80) < 1e-9 else 1.2815515655446004
    num = ((z_alpha + z_beta) ** 2) * (p0 * (1.0 - p0) + p1 * (1.0 - p1))
    den = (p1 - p0) ** 2
    return math.ceil(num / den)


def check_experiment(payload: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    metrics: dict[str, Any] = {}

    variants = payload.get("variants")
    if not isinstance(variants, list) or len(variants) < 2:
        return {
            "check": "experiment",
            "passed": False,
            "verdict": "BLOCKED_INVALID_DESIGN",
            "errors": ["Experiment requires at least 2 variants."],
            "warnings": [],
            "metrics": {},
        }

    srm_alpha = payload.get("srm_alpha", 0.001)
    if type(srm_alpha) not in (int, float) or not 1e-6 <= srm_alpha <= 0.01:
        raise InvalidInput("srm_alpha must be a finite JSON number in [1e-6, 0.01].")
    justification = payload.get("srm_alpha_justification")
    if srm_alpha != 0.001 and not (isinstance(justification, str) and justification.strip()):
        raise InvalidInput("srm_alpha_justification is required for a non-default srm_alpha.")
    metrics["srm_alpha"] = srm_alpha
    alpha = float(payload.get("alpha", 0.05))
    for variant in variants:
        if not isinstance(variant, dict):
            raise InvalidInput("Each variants entry must be a JSON object.")
        ratio = variant.get("expected_ratio")
        assigned = variant.get("assigned_count")
        if type(ratio) not in (int, float) or not 0 < ratio <= 1:
            raise InvalidInput("Each expected_ratio must be a finite JSON number in (0, 1].")
        if type(assigned) is not int or assigned <= 0:
            raise InvalidInput("Each assigned_count must be a positive JSON integer.")
    ratio_sum = sum(v["expected_ratio"] for v in variants)
    if abs(ratio_sum - 1.0) > 1e-4:
        errors.append(f"Expected allocation ratios must sum to 1.0 (got {ratio_sum:.6f}).")

    total_assigned = sum(int(v.get("assigned_count", 0)) for v in variants)
    if total_assigned <= 0:
        errors.append("Total assigned_count must be > 0.")
        return {
            "check": "experiment",
            "passed": False,
            "verdict": "BLOCKED_INVALID_DESIGN",
            "errors": errors,
            "warnings": warnings,
            "metrics": metrics,
        }

    chi2 = 0.0
    for v in variants:
        expected = total_assigned * float(v.get("expected_ratio", 0.0))
        observed = int(v.get("assigned_count", 0))
        if expected > 0:
            chi2 += ((observed - expected) ** 2) / expected
    df = len(variants) - 1
    srm_p = _chi2_upper_tail_p(chi2, df)
    srm_detected = srm_p < srm_alpha
    metrics["srm_chi2"] = round(chi2, 6)
    metrics["srm_df"] = df
    metrics["srm_p_value"] = srm_p
    metrics["srm_detected"] = srm_detected
    if srm_detected:
        errors.append(
            f"Sample Ratio Mismatch (SRM) detected: chi2={chi2:.4f}, df={df}, p={srm_p:.6g} < {srm_alpha}. "
            "Experiment results are INVALID and MUST NOT be shipped until assignment/logging bias is fixed."
        )

    # Assignment vs Exposure check
    if not strict_bool(payload.get("assignment_exposure_separated", True), "assignment_exposure_separated"):
        errors.append("Assignment and exposure events are conflated; separate Assignment (ITT) from Exposure.")
    for v in variants:
        if "exposed_count" in v and int(v["exposed_count"]) > int(v["assigned_count"]):
            errors.append(
                f"Variant '{v.get('name')}' has exposed_count ({v['exposed_count']}) > assigned_count ({v['assigned_count']})."
            )

    # CUPED pre-experiment covariate check
    cuped_invalid = False
    cuped = payload.get("cuped", {})
    if not isinstance(cuped, dict):
        raise InvalidInput("cuped must be a JSON object.")
    cuped_enabled = strict_bool(cuped.get("enabled", False), "cuped.enabled")
    pre_experiment = strict_bool(cuped.get("covariate_is_pre_experiment", False), "cuped.covariate_is_pre_experiment")
    unaffected = strict_bool(cuped.get("covariate_unaffected_by_assignment", False), "cuped.covariate_unaffected_by_assignment")
    if cuped_enabled:
        if not (pre_experiment and unaffected):
            cuped_invalid = True
            errors.append(
                "Invalid CUPED covariate: covariate MUST be measured strictly pre-experiment and unaffected by treatment assignment."
            )
        elif "correlation_rho" in cuped:
            rho = float(cuped["correlation_rho"])
            metrics["cuped_variance_reduction_pct"] = round((rho ** 2) * 100.0, 2)

    # Guardrails
    blocking_guardrail = False
    guardrails = payload.get("guardrails", [])
    if not isinstance(guardrails, list):
        raise InvalidInput("guardrails must be a JSON array.")
    for index, g in enumerate(guardrails):
        if not isinstance(g, dict):
            raise InvalidInput(f"guardrails[{index}] must be a JSON object.")
        regressed = strict_bool(g.get("regressed"), f"guardrails[{index}].regressed")
        severity = g.get("severity", "blocking")
        if not isinstance(severity, str) or severity.lower() not in {"blocking", "non-blocking", "non_blocking", "advisory", "warning"}:
            raise InvalidInput(f"guardrails[{index}].severity must be blocking or non-blocking.")
        if regressed:
            if severity.lower() == "blocking":
                blocking_guardrail = True
                errors.append(f"Blocking guardrail regressed: {g.get('name', 'unnamed')}.")
            else:
                warnings.append(f"Non-blocking guardrail regressed: {g.get('name', 'unnamed')}.")

    # Power / MDE check
    underpowered = False
    if "baseline_rate" in payload and "mde_relative" in payload:
        req_n = _required_sample_per_variant_proportion(
            float(payload["baseline_rate"]),
            float(payload["mde_relative"]),
            alpha=alpha,
            power=float(payload.get("power", 0.80)),
        )
        min_n = min(int(v.get("assigned_count", 0)) for v in variants)
        metrics["required_n_per_variant"] = req_n
        metrics["observed_min_n_per_variant"] = min_n
        if min_n < req_n:
            underpowered = True
            warnings.append(f"Experiment underpowered: min variant n={min_n} < required n={req_n} per variant.")

    # Effect estimator (2-variant proportion Z-test OR Delta Method ratio metric)
    stat_sig_positive = False
    metric_type = str(payload.get("metric_type", "proportion")).lower()
    if len(variants) == 2:
        c, t = variants[0], variants[1]
        if metric_type == "proportion" and "conversions" in c and "conversions" in t:
            nc = int(c["assigned_count"])
            nt = int(t["assigned_count"])
            xc = int(c["conversions"])
            xt = int(t["conversions"])
            pc = xc / nc
            pt = xt / nt
            abs_lift = pt - pc
            rel_lift = (abs_lift / pc) if pc > 0 else None
            se = math.sqrt((pc * (1.0 - pc) / nc) + (pt * (1.0 - pt) / nt))
            z = (abs_lift / se) if se > 0 else 0.0
            p_val = _normal_two_sided_p(z)
            ci_low = abs_lift - 1.959963984540054 * se
            ci_high = abs_lift + 1.959963984540054 * se
            metrics.update(
                {
                    "estimator": "two_proportion_z_test",
                    "control_rate": round(pc, 6),
                    "treatment_rate": round(pt, 6),
                    "absolute_lift": round(abs_lift, 6),
                    "relative_lift": round(rel_lift, 6) if rel_lift is not None else None,
                    "z_score": round(z, 4),
                    "p_value": p_val,
                    "ci_95_absolute": [round(ci_low, 6), round(ci_high, 6)],
                }
            )
            if p_val < alpha and abs_lift > 0:
                stat_sig_positive = True
        elif metric_type == "ratio":
            req_fields = ("numerator_mean", "denominator_mean", "var_num", "var_den", "cov_num_den")
            if all(k in c and k in t for k in req_fields):
                def _ratio_stats(v: dict[str, Any]) -> tuple[float, float]:
                    n = int(v["assigned_count"])
                    my = float(v["numerator_mean"])
                    mx = float(v["denominator_mean"])
                    vy = float(v["var_num"])
                    vx = float(v["var_den"])
                    cxy = float(v["cov_num_den"])
                    r = my / mx
                    var_r = (vy - 2.0 * r * cxy + (r ** 2) * vx) / (n * (mx ** 2))
                    return r, max(0.0, var_r)

                rc, var_rc = _ratio_stats(c)
                rt, var_rt = _ratio_stats(t)
                diff = rt - rc
                se = math.sqrt(var_rc + var_rt)
                z = (diff / se) if se > 0 else 0.0
                p_val = _normal_two_sided_p(z)
                metrics.update(
                    {
                        "estimator": "delta_method_ratio",
                        "control_ratio": round(rc, 6),
                        "treatment_ratio": round(rt, 6),
                        "absolute_lift": round(diff, 6),
                        "relative_lift": round(diff / rc, 6) if rc != 0 else None,
                        "delta_se": round(se, 6),
                        "z_score": round(z, 4),
                        "p_value": p_val,
                    }
                )
                if p_val < alpha and diff > 0:
                    stat_sig_positive = True

    # Precedence: SRM > Invalid Design/CUPED > Blocking Guardrail > Underpowered > Ship Candidate > Inconclusive
    if srm_detected:
        verdict = "BLOCKED_SRM"
    elif cuped_invalid or (len(errors) > 0 and not blocking_guardrail):
        verdict = "BLOCKED_INVALID_DESIGN"
    elif blocking_guardrail:
        verdict = "BLOCKED_GUARDRAIL"
    elif underpowered:
        verdict = "UNDERPOWERED"
    elif stat_sig_positive:
        verdict = "SHIP_CANDIDATE"
    else:
        verdict = "INCONCLUSIVE"

    return {
        "check": "experiment",
        "passed": len(errors) == 0,
        "verdict": verdict,
        "errors": errors,
        "warnings": warnings,
        "metrics": metrics,
    }


def check_dsar_plan(payload: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []

    warehouse_covered = strict_bool(payload.get("warehouse_tables_covered", False), "warehouse_tables_covered")
    if not warehouse_covered:
        errors.append("Local analytics warehouse identity/event tables are not covered by DSAR deletion workflow.")

    configured = {str(v).strip().lower() for v in payload.get("configured_vendors", []) if str(v).strip()}
    wired = {str(v).strip().lower() for v in payload.get("vendor_deletion_apis_wired", []) if str(v).strip()}

    if strict_bool(payload.get("warehouse_only", False), "warehouse_only") and configured:
        errors.append(
            f"warehouse_only DSAR does NOT satisfy UU PDP/GDPR when third-party vendors ({sorted(configured)}) hold user copies."
        )

    missing_vendors = sorted(configured - wired)
    if missing_vendors:
        errors.append(
            f"DSAR_INCOMPLETE_VENDOR_COVERAGE: Missing deletion API / retention SLA orchestration for vendors: {', '.join(missing_vendors)}."
        )

    sla_days = payload.get("vendor_deletion_sla_days", {})
    max_sla = int(payload.get("max_allowed_sla_days", 30))
    if isinstance(sla_days, dict):
        for vendor, days in sla_days.items():
            if int(days) > max_sla:
                errors.append(f"Vendor '{vendor}' deletion SLA ({days}d) exceeds max allowed ({max_sla}d).")

    if payload.get("suppression_tombstone_hashed") is not True:
        warnings.append("Retain keyed HMAC-SHA256 suppression/opt-out tombstone so erased users are not re-targeted.")

    return {
        "check": "dsar_plan",
        "passed": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
    }


def run_self_test() -> dict[str, Any]:
    probes: list[tuple[str, bool]] = []

    # PRECISION-1: Valid repeatable event with occurrence-unique UUIDv7 and zero PII
    r1 = check_event(
        {
            "event": "Search_Queried",
            "event_id": "019355c4-7f1e-7a22-9b10-4c9e3a812001",
            "schema_version": 2,
            "timestamp": "2026-11-22T10:15:00Z",
            "anonymous_id": "anon_98ab72",
            "repeatable": True,
            "event_id_strategy": "occurrence_uuid",
            "consent_analytics": True,
            "properties": {"query_length": 14, "result_count": 23},
        }
    )
    probes.append(("PRECISION-1: Valid repeatable event with UUIDv7 and zero PII passes", r1["passed"] is True))

    # RECALL-1: Repeatable event using static entity hash + raw PII email/nik rejected
    r2 = check_event(
        {
            "event": "cart_item_added",
            "event_id": "sha256_cart_123",
            "schema_version": 1,
            "timestamp": "2026-11-22T10:15:00Z",
            "anonymous_id": "anon_1",
            "repeatable": True,
            "event_id_strategy": "static_entity_hash",
            "properties": {"email": "user@example.com", "nik": "3171000000000001"},
        }
    )
    probes.append(
        (
            "RECALL-1: Bad naming, static entity hash on repeatable event, and raw PII rejected",
            r2["passed"] is False and len(r2["errors"]) >= 3,
        )
    )

    # RECALL-2 (Monarch Benchmark): +12% lift, p~0.02, BUT SRM p~0.0002 -> MUST return BLOCKED_SRM
    r3 = check_experiment(
        {
            "assignment_exposure_separated": True,
            "variants": [
                {"name": "control", "expected_ratio": 0.5, "assigned_count": 10200, "conversions": 1020},
                {"name": "treatment", "expected_ratio": 0.5, "assigned_count": 9680, "conversions": 1084},
            ],
        }
    )
    probes.append(
        (
            "RECALL-2 (Monarch Benchmark): Positive lift with SRM p<0.001 forces BLOCKED_SRM",
            r3["verdict"] == "BLOCKED_SRM" and r3["metrics"]["srm_detected"] is True and r3["metrics"]["p_value"] < 0.05,
        )
    )

    # PRECISION-2: Clean 50/50 split, powered, valid pre-experiment CUPED -> SHIP_CANDIDATE
    r4 = check_experiment(
        {
            "assignment_exposure_separated": True,
            "baseline_rate": 0.10,
            "mde_relative": 0.10,
            "cuped": {
                "enabled": True,
                "covariate_is_pre_experiment": True,
                "covariate_unaffected_by_assignment": True,
                "correlation_rho": 0.5,
            },
            "variants": [
                {"name": "control", "expected_ratio": 0.5, "assigned_count": 16000, "conversions": 1600},
                {"name": "treatment", "expected_ratio": 0.5, "assigned_count": 15940, "conversions": 1801},
            ],
        }
    )
    probes.append(
        (
            "PRECISION-2: Clean split, powered lift, valid pre-experiment CUPED -> SHIP_CANDIDATE",
            r4["verdict"] == "SHIP_CANDIDATE" and r4["metrics"]["cuped_variance_reduction_pct"] == 25.0,
        )
    )

    # RECALL-3: Post-assignment CUPED covariate rejected
    r5 = check_experiment(
        {
            "assignment_exposure_separated": True,
            "cuped": {
                "enabled": True,
                "covariate_is_pre_experiment": False,
                "covariate_unaffected_by_assignment": False,
            },
            "variants": [
                {"name": "control", "expected_ratio": 0.5, "assigned_count": 5000, "conversions": 500},
                {"name": "treatment", "expected_ratio": 0.5, "assigned_count": 5000, "conversions": 575},
            ],
        }
    )
    probes.append(
        ("RECALL-3: Post-assignment CUPED leakage returns BLOCKED_INVALID_DESIGN", r5["verdict"] == "BLOCKED_INVALID_DESIGN")
    )

    # PRECISION-3: Delta Method ratio metric (revenue per session / CTR per user)
    r6 = check_experiment(
        {
            "assignment_exposure_separated": True,
            "metric_type": "ratio",
            "variants": [
                {
                    "name": "control",
                    "expected_ratio": 0.5,
                    "assigned_count": 10000,
                    "numerator_mean": 2.0,
                    "denominator_mean": 4.0,
                    "var_num": 6.0,
                    "var_den": 8.0,
                    "cov_num_den": 4.0,
                },
                {
                    "name": "treatment",
                    "expected_ratio": 0.5,
                    "assigned_count": 10020,
                    "numerator_mean": 2.2,
                    "denominator_mean": 4.0,
                    "var_num": 6.5,
                    "var_den": 8.0,
                    "cov_num_den": 4.1,
                },
            ],
        }
    )
    probes.append(
        (
            "PRECISION-3: Delta Method computes ratio variance and yields SHIP_CANDIDATE",
            r6["verdict"] == "SHIP_CANDIDATE" and r6["metrics"]["estimator"] == "delta_method_ratio",
        )
    )

    # RECALL-4: Warehouse-only DSAR fails when PostHog/GA4 are configured
    r7 = check_dsar_plan(
        {
            "warehouse_tables_covered": True,
            "warehouse_only": True,
            "configured_vendors": ["posthog", "ga4"],
            "vendor_deletion_apis_wired": [],
            "suppression_tombstone_hashed": True,
        }
    )
    probes.append(
        (
            "RECALL-4: Warehouse-only DSAR rejected when third-party vendors hold user data",
            r7["passed"] is False and any("DSAR_INCOMPLETE_VENDOR_COVERAGE" in e for e in r7["errors"]),
        )
    )

    passed = sum(1 for _, ok in probes if ok)
    return {
        "tool": "analytics_experiment_verifier.py",
        "total_probes": len(probes),
        "passed": passed,
        "failed": len(probes) - passed,
        "all_passed": passed == len(probes),
        "results": [{"probe": name, "passed": ok} for name, ok in probes],
    }


def _load_json(path_str: str) -> dict[str, Any]:
    raw = json.loads(Path(path_str).read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"Expected JSON object in {path_str}")
    return raw


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Offline Analytics, Experimentation & DSAR Verifier")
    parser.add_argument("--self-test", action="store_true", help="Run built-in precision & recall probes")
    parser.add_argument("--check-event", metavar="PATH", help="Validate event JSON against taxonomy/PII/event_id rules")
    parser.add_argument("--check-experiment", metavar="PATH", help="Validate SRM, power, estimator, CUPED & guardrails")
    parser.add_argument("--check-dsar-plan", metavar="PATH", help="Validate warehouse + vendor DSAR deletion coverage")
    args = parser.parse_args(argv)

    if args.self_test:
        res = run_self_test()
        print(json.dumps(res, indent=2))
        return 0 if res["all_passed"] else 1

    if args.check_event:
        res = check_event(_load_json(args.check_event))
        print(json.dumps(res, indent=2))
        return 0 if res["passed"] else 1

    if args.check_experiment:
        res = check_experiment(_load_json(args.check_experiment))
        print(json.dumps(res, indent=2))
        return 0 if res["passed"] else 1

    if args.check_dsar_plan:
        res = check_dsar_plan(_load_json(args.check_dsar_plan))
        print(json.dumps(res, indent=2))
        return 0 if res["passed"] else 1

    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(run_checked_cli(main))
