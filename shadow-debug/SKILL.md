---
name: shadow-debug
description: "Systematic Root-Cause Debugging Engineering. Use when diagnosing unexpected bugs, 500 errors, flaky tests, memory leaks, race symptoms, environment drift, or misleading stack traces. Do NOT use for post-prod SLA/Harwat process (shadow-maintain), telemetry setup (shadow-observe), load benchmarking (shadow-perf), or broad code restructuring (shadow-refactor)."
---

# `/shadow-debug` — Systematic Debugging & Root-Cause Engineering

- **Owner:** Causal diagnosis of software failures with minimal reproduction and red-before/green-after proof.
- **Boundaries:** Post-prod SLA/Harwat triage (`shadow-maintain`), OTel/alert platform setup (`shadow-observe`), load tests (`shadow-perf`), code-structure refactor (`shadow-refactor`).

## 1. Preconditions, Permissions & Failure Handling
- **Default Access:** Read-only inspection (`read_repository`, `run_local_tests`). Never mutate production DBs/containers or expose secrets/PII in logs or `debug-report.md`.
- **Missing Evidence Rule:** If logs, stack traces, or environment reproduction are unavailable, mark missing evidence explicitly and propose safe instrumentation rather than guessing root cause from a single coincidental error line.
- **Escalation:** If diagnosis requires live production data access without authorization, stop at safe local reproduction plan + escalation request.

## 2. 8-Step Scientific Debugging Playbook
Read [`methodologies/SCIENTIFIC-DEBUGGING-AND-FAULT-TREES.md`](methodologies/SCIENTIFIC-DEBUGGING-AND-FAULT-TREES.md) and [`playbooks/DEBUG-REPORT-AND-REPRO-TEMPLATE.md`](playbooks/DEBUG-REPORT-AND-REPRO-TEMPLATE.md) when executing complex diagnosis:
1. **Capture Symptom & Scope:** Expected vs actual behavior, severity, first occurrence, affected env/version.
2. **Build Redacted Timeline:** Correlate logs, W3C `traceparent` / `requestId`, commits (`git bisect`), and env drift; redact tokens/PII.
3. **Rank Testable Hypotheses (>= 2):** Pair each hypothesis with explicit **disconfirming observations** and safe probes (never stop at the first plausible log line).
4. **Minimal Isolated Reproduction:** Create a minimal deterministic test or fixture reproducing the failure (`FAIL` exit code != `0`).
5. **Pinpoint Minimal Root Cause:** Separate symptom, contributing factor, and causal mechanism using targeted instrumentation or bisect.
6. **Failing-Before Regression Test:** Record red-before run proving the test catches the exact bug.
7. **Minimal Behavior-Preserving Fix:** Apply smallest consistent change (`§4.1`); execute targeted + adjacent regression suites (`PASS` exit code == `0`).
8. **Report & Recurrence Prevention:** Emit `debug-report.md` using the shared evidence envelope (`PASS | FAIL | NOT_RUN | BLOCKED`).

## 3. Examples (Happy, Ambiguous, Failure) & Deterministic Gate
- **Happy Path:** API returns intermittent `500` -> trace shows worker ack race -> 2 hypotheses tested -> red test added -> atomic fix -> green suite.
- **Ambiguous Case:** Bug only occurs in staging, not local -> compare env vars, lockfiles, timezone, pool limits before touching code.
- **Failure / Must-Reject:** Report claims root cause solely from 1 coincidental log line with no disconfirming probe or failing-before test -> **BLOCKED** by `debug_hypothesis_gate.py`.

```powershell
python "shadow-debug/scripts/debug_hypothesis_gate.py" --self-test
python "shadow-debug/scripts/debug_hypothesis_gate.py" --validate-report path/to/debug-report.json
```

## 4. Execution Approval & Intent Boundary (`L0`–`L4`)
- Log/config/code diagnosis is `L0_READ_ONLY`; minimal local reproduction tests are bounded `L1_SAFE_VERIFICATION` inside verified local/sandbox targets. Debugging NEVER authorizes `L3` stress/load testing or `L4` staging/production/unknown mutations without the 7-part approval contract (`shadow-monarch/scripts/execution_approval_gate.py`).
