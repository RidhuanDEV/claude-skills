#!/usr/bin/env python3
"""Deterministic observability & telemetry hygiene verifier for shadow-observe.

Validates Prometheus metric cardinality, multi-window SLO burn-rate alerting,
OpenTelemetry sampling configuration, and structured JSON log redaction / anti-CRLF hygiene.
Zero external dependencies (Python stdlib only).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

HIGH_CARDINALITY_LABELS = frozenset({
    "user_id",
    "userid",
    "request_id",
    "requestid",
    "trace_id",
    "traceid",
    "span_id",
    "spanid",
    "email",
    "raw_url",
    "raw_path",
    "url",
    "ip",
    "ip_address",
    "client_ip",
    "session_id",
    "sessionid",
    "order_id",
    "orderid",
    "uuid",
    "token",
    "phone",
    "nik",
    "customer_id",
    "account_id",
})

SENSITIVE_LOG_KEY_RE = re.compile(
    r"^(?:authorization|cookie|set-cookie|password|passwd|secret|token|access_token|refresh_token|api_?key|nik|otp|credit_?card|cvv|private_?key)$",
    re.IGNORECASE,
)

BEARER_OR_JWT_RE = re.compile(
    r"(?:Bearer\s+[A-Za-z0-9._\-~+/]+=*|eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{5,})"
)

RAW_UUID_IN_ROUTE_RE = re.compile(
    r"/[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}(?:/|$)"
)
RAW_NUMERIC_ID_IN_ROUTE_RE = re.compile(r"/\d{4,}(?:/|$)")
ISO_TS_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$")
ALLOWED_LOG_LEVELS = frozenset({"debug", "info", "warn", "warning", "error", "fatal"})
REDACTED_MARKERS = frozenset({"[REDACTED]", "***", "<redacted>"})


def check_metrics_config(config: Any) -> list[dict[str, str]]:
    """Audit Prometheus metrics labels, SLO burn-rate alerts, and OTel sampling."""
    violations: list[dict[str, str]] = []
    if not isinstance(config, dict) or not config:
        return [{"code": "EMPTY_CONFIG", "detail": "Metrics/alerting configuration must be a non-empty JSON object."}]

    metrics = config.get("metrics", [])
    if not isinstance(metrics, list):
        violations.append({"code": "INVALID_METRICS", "detail": "`metrics` must be an array."})
    else:
        for idx, metric in enumerate(metrics):
            if not isinstance(metric, dict):
                violations.append({"code": "INVALID_METRIC_ENTRY", "detail": f"metrics[{idx}] must be an object."})
                continue
            name = str(metric.get("name", f"metrics[{idx}]"))
            labels = metric.get("labels", [])
            if not isinstance(labels, list):
                violations.append({"code": "INVALID_LABELS", "detail": f"Metric `{name}` labels must be a list."})
                continue
            for raw_label in labels:
                label = str(raw_label).strip().lower()
                if label in HIGH_CARDINALITY_LABELS:
                    violations.append({
                        "code": "HIGH_CARDINALITY_LABEL",
                        "detail": f"Metric `{name}` attaches unbounded label `{raw_label}`; move high-cardinality IDs to OTel spans and structured logs.",
                    })

    alerts = config.get("alerts", [])
    if not isinstance(alerts, list):
        violations.append({"code": "INVALID_ALERTS", "detail": "`alerts` must be an array."})
    else:
        for idx, alert in enumerate(alerts):
            if not isinstance(alert, dict):
                violations.append({"code": "INVALID_ALERT_ENTRY", "detail": f"alerts[{idx}] must be an object."})
                continue
            name = str(alert.get("name", f"alerts[{idx}]"))
            severity = str(alert.get("severity", "")).lower()
            paging = bool(alert.get("paging", severity in {"critical", "p1", "page"}))

            if paging:
                runbook = str(alert.get("runbook_url", "") or alert.get("triage_command", "")).strip()
                if not runbook:
                    violations.append({
                        "code": "PAGING_ALERT_MISSING_RUNBOOK",
                        "detail": f"Paging alert `{name}` lacks `runbook_url` or actionable `triage_command`.",
                    })

                alert_type = str(alert.get("type", "")).lower()
                expr = str(alert.get("expr", "")).lower()
                symptom_based = alert.get("symptom_based")
                if symptom_based is False or (
                    ("cpu" in expr or "memory" in expr)
                    and "5xx" not in expr
                    and "error" not in expr
                    and "latency" not in expr
                    and "burn" not in expr
                    and "saturation" not in expr
                    and "disk" not in expr
                    and alert_type != "capacity_cliff"
                ):
                    violations.append({
                        "code": "CAUSE_ONLY_PAGING_ALERT",
                        "detail": f"Paging alert `{name}` pages on noisy resource cause without user-facing symptom or capacity-cliff justification.",
                    })

                if alert_type == "burn_rate":
                    long_w = str(alert.get("long_window", "")).strip()
                    short_w = str(alert.get("short_window", "")).strip()
                    if not long_w or not short_w:
                        violations.append({
                            "code": "SINGLE_WINDOW_BURN_RATE",
                            "detail": f"Burn-rate alert `{name}` must configure both `long_window` and `short_window` to prevent stale paging after recovery.",
                        })

    sampling = config.get("otel_sampling")
    if sampling is not None:
        if not isinstance(sampling, dict):
            violations.append({"code": "INVALID_SAMPLING", "detail": "`otel_sampling` must be an object."})
        else:
            head_rate = sampling.get("head_sample_rate", 1.0)
            tail_policy = sampling.get("tail_sampling", {})
            if isinstance(head_rate, (int, float)) and head_rate < 1.0:
                if not isinstance(tail_policy, dict) or not (
                    tail_policy.get("keep_5xx") and tail_policy.get("keep_slow_traces")
                ):
                    violations.append({
                        "code": "HEAD_SAMPLING_DROPS_ERRORS",
                        "detail": "Head sampling < 1.0 without tail-based `keep_5xx: true` and `keep_slow_traces: true` risks dropping critical incident traces.",
                    })

    return violations


def _scan_log_values(obj: Any, path: str, violations: list[dict[str, str]]) -> None:
    if isinstance(obj, dict):
        for k, v in obj.items():
            key_path = f"{path}.{k}" if path else str(k)
            if SENSITIVE_LOG_KEY_RE.match(str(k)):
                if not (isinstance(v, str) and v.strip() in REDACTED_MARKERS):
                    violations.append({
                        "code": "UNREDACTED_SENSITIVE_FIELD",
                        "detail": f"Sensitive log field `{key_path}` is not redacted (`[REDACTED]`).",
                    })
                    continue
            _scan_log_values(v, key_path, violations)
    elif isinstance(obj, list):
        for idx, item in enumerate(obj):
            _scan_log_values(item, f"{path}[{idx}]", violations)
    elif isinstance(obj, str):
        if "\n" in obj or "\r" in obj:
            violations.append({
                "code": "CRLF_LOG_INJECTION",
                "detail": f"Field `{path}` contains raw CR/LF newline characters that enable log forging.",
            })
        if BEARER_OR_JWT_RE.search(obj):
            violations.append({
                "code": "SECRET_TOKEN_LEAK",
                "detail": f"Field `{path}` contains an unredacted Bearer token or JWT.",
            })


def check_log_sample(log_entry: Any) -> list[dict[str, str]]:
    """Audit a structured JSON log event for schema completeness, route cardinality, PII redaction, and CRLF hygiene."""
    violations: list[dict[str, str]] = []
    if not isinstance(log_entry, dict) or not log_entry:
        return [{"code": "EMPTY_LOG_SAMPLE", "detail": "Log sample must be a non-empty JSON object."}]

    ts = log_entry.get("ts") or log_entry.get("timestamp")
    if not isinstance(ts, str) or not ISO_TS_RE.match(ts.strip()):
        violations.append({
            "code": "MISSING_OR_INVALID_TIMESTAMP",
            "detail": "Structured log must include an ISO-8601 `ts` or `timestamp` field.",
        })

    level = str(log_entry.get("level", "")).lower()
    if level not in ALLOWED_LOG_LEVELS:
        violations.append({
            "code": "INVALID_LOG_LEVEL",
            "detail": f"Log `level` must be one of {sorted(ALLOWED_LOG_LEVELS)}.",
        })

    if not str(log_entry.get("event", "") or log_entry.get("msg", "")).strip():
        violations.append({
            "code": "MISSING_EVENT_NAME",
            "detail": "Structured log must include a canonical `event` (or `msg`) identifier.",
        })

    has_corr = any(
        isinstance(log_entry.get(k), str) and log_entry.get(k, "").strip()
        for k in ("requestId", "request_id", "traceId", "trace_id", "traceparent")
    )
    if not has_corr:
        violations.append({
            "code": "MISSING_CORRELATION_ID",
            "detail": "Structured log lacks `requestId`/`traceId`/`traceparent` correlation key.",
        })

    for route_key in ("routeTemplate", "route_template", "route"):
        route_val = log_entry.get(route_key)
        if isinstance(route_val, str):
            if RAW_UUID_IN_ROUTE_RE.search(route_val) or RAW_NUMERIC_ID_IN_ROUTE_RE.search(route_val):
                violations.append({
                    "code": "UNNORMALIZED_ROUTE_TEMPLATE",
                    "detail": f"`{route_key}` (`{route_val}`) contains a raw UUID or numeric ID instead of a parameterized template (e.g. `/api/v1/orders/:id`).",
                })

    _scan_log_values(log_entry, "", violations)
    return violations


def run_self_test() -> dict[str, Any]:
    probes: list[tuple[str, bool]] = []

    # PRECISION-1: Clean metrics + multi-window burn-rate + tail sampling
    v = check_metrics_config({
        "metrics": [
            {"name": "http_server_request_duration_seconds", "labels": ["service", "method", "route_template", "status_class"]}
        ],
        "alerts": [
            {
                "name": "ApiFastErrorBudgetBurn",
                "severity": "critical",
                "paging": True,
                "type": "burn_rate",
                "long_window": "1h",
                "short_window": "5m",
                "expr": "slo:http_5xx_ratio:1h > 14.4 * 0.001 and slo:http_5xx_ratio:5m > 14.4 * 0.001",
                "runbook_url": "https://runbooks.internal/api-fast-burn",
            }
        ],
        "otel_sampling": {
            "head_sample_rate": 0.1,
            "tail_sampling": {"keep_5xx": True, "keep_slow_traces": True},
        },
    })
    probes.append(("PRECISION-1: Bounded labels, multi-window burn-rate & tail sampling pass", len(v) == 0))

    # RECALL-1: High-cardinality labels & paging alert without runbook
    v = check_metrics_config({
        "metrics": [{"name": "http_requests_total", "labels": ["user_id", "request_id", "raw_url"]}],
        "alerts": [{"name": "CheckoutDown", "severity": "critical", "paging": True, "expr": "http_5xx_rate > 0.05"}],
    })
    codes = {item["code"] for item in v}
    probes.append((
        "RECALL-1: Rejects unbounded user_id/request_id/raw_url labels & missing runbook",
        "HIGH_CARDINALITY_LABEL" in codes and "PAGING_ALERT_MISSING_RUNBOOK" in codes,
    ))

    # RECALL-2: Single-window burn rate & noisy CPU paging alert
    v = check_metrics_config({
        "alerts": [
            {
                "name": "SingleWindowBurn",
                "severity": "critical",
                "paging": True,
                "type": "burn_rate",
                "long_window": "1h",
                "expr": "slo:error_burn:1h > 14.4",
                "runbook_url": "https://runbooks.internal/burn",
            },
            {
                "name": "HighCpuNoise",
                "severity": "critical",
                "paging": True,
                "expr": "avg(node_cpu_seconds_total) > 0.80",
                "runbook_url": "https://runbooks.internal/cpu",
            },
        ]
    })
    codes = {item["code"] for item in v}
    probes.append((
        "RECALL-2: Rejects single-window burn-rate & cause-only CPU paging alert",
        "SINGLE_WINDOW_BURN_RATE" in codes and "CAUSE_ONLY_PAGING_ALERT" in codes,
    ))

    # PRECISION-2: Canonical wide-event JSON log passes
    v = check_log_sample({
        "ts": "2026-11-22T10:15:30.123Z",
        "level": "info",
        "event": "http.request.completed",
        "requestId": "req_01J9X2K9F8",
        "traceId": "4bf92f3577b34da6a3ce929d0e0e4736",
        "routeTemplate": "/api/v1/orders/:orderId",
        "statusCode": 200,
        "durationMs": 42,
        "headers": {"authorization": "[REDACTED]"},
    })
    probes.append(("PRECISION-2: Canonical wide-event JSON log with redacted auth passes", len(v) == 0))

    # RECALL-3: Bearer token, raw NIK, and raw UUID in routeTemplate rejected
    v = check_log_sample({
        "ts": "2026-11-22T10:15:30Z",
        "level": "error",
        "event": "order.failed",
        "requestId": "req_01J9X",
        "routeTemplate": "/api/v1/orders/550e8400-e29b-41d4-a716-446655440000",
        "nik": "3174011205900001",
        "debugHeader": "Bearer supersecret_token_999",
    })
    codes = {item["code"] for item in v}
    probes.append((
        "RECALL-3: Rejects raw NIK, Bearer leak & raw UUID in routeTemplate",
        {"UNREDACTED_SENSITIVE_FIELD", "SECRET_TOKEN_LEAK", "UNNORMALIZED_ROUTE_TEMPLATE"}.issubset(codes),
    ))

    # RECALL-4: CRLF log injection rejected
    v = check_log_sample({
        "ts": "2026-11-22T10:15:30Z",
        "level": "warn",
        "event": "auth.login_failed",
        "requestId": "req_01J9Y",
        "username": "alice\n{\"level\":\"info\",\"event\":\"auth.admin_granted\"}",
    })
    codes = {item["code"] for item in v}
    probes.append(("RECALL-4: Rejects unescaped CRLF log forging payload", "CRLF_LOG_INJECTION" in codes))

    # BOUNDARY-1: Empty payload rejected gracefully
    v_empty_cfg = check_metrics_config({})
    v_empty_log = check_log_sample({})
    probes.append((
        "BOUNDARY-1: Rejects empty config and empty log payload gracefully",
        len(v_empty_cfg) == 1 and len(v_empty_log) == 1,
    ))

    passed = sum(1 for _, ok in probes if ok)
    return {
        "tool": "telemetry_hygiene_verifier.py",
        "total_probes": len(probes),
        "passed": passed,
        "failed": len(probes) - passed,
        "all_passed": passed == len(probes),
        "results": [{"probe": name, "passed": ok} for name, ok in probes],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify observability telemetry hygiene (cardinality, alerts, sampling, logs).")
    parser.add_argument("--self-test", action="store_true", help="Run built-in precision/recall falsification probes.")
    parser.add_argument("--check-metrics-config", type=Path, help="Path to JSON metrics/alerts/sampling config.")
    parser.add_argument("--check-log-sample", type=Path, help="Path to JSON structured log sample.")
    args = parser.parse_args(argv)

    if args.self_test:
        report = run_self_test()
        print(json.dumps(report, indent=2))
        return 0 if report["all_passed"] else 1

    violations: list[dict[str, str]] = []
    checked = False

    if args.check_metrics_config:
        checked = True
        data = json.loads(args.check_metrics_config.read_text(encoding="utf-8"))
        violations.extend(check_metrics_config(data))

    if args.check_log_sample:
        checked = True
        data = json.loads(args.check_log_sample.read_text(encoding="utf-8"))
        violations.extend(check_log_sample(data))

    if not checked:
        parser.print_help()
        return 2

    output = {"status": "PASS" if not violations else "FAIL", "violation_count": len(violations), "violations": violations}
    print(json.dumps(output, indent=2))
    return 0 if not violations else 1


if __name__ == "__main__":
    sys.exit(main())
