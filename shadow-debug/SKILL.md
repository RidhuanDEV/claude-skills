---
name: shadow-debug
description: "Systematic Root-Cause Debugging Engineering. Use when diagnosing unexpected bugs, 500 errors, flaky tests, memory leaks, CPU/event-loop freezes, deadlocks, race conditions, environment drift, or misleading stack traces. Do NOT use for post-prod SLA/Harwat process (shadow-maintain), telemetry setup (shadow-observe), load benchmarking (shadow-perf), or broad code restructuring (shadow-refactor)."
---

# `/shadow-debug` — Systematic Debugging, Production Forensics & Root-Cause Engineering

- **Owner:** Causal diagnosis of software failures via `>= 2` competing hypotheses, falsification probes, minimal isolated reproduction, runtime/concurrency/drift forensics, and red-before/green-after proof.
- **Boundaries:** Post-prod SLA/Harwat triage & postmortems (`shadow-maintain`), OTel/SLO alerting platform setup (`shadow-observe`), Pre-UAT `k6` load testing (`shadow-perf`), broad code restructuring (`shadow-refactor`), and suite-wide test engineering (`shadow-test`).

## Reference Guide

Load ONLY the 1–2 modular playbooks needed for the active debugging subtask:

| Module | Topic | Load When |
| :--- | :--- | :--- |
| [01-scientific-hypothesis-falsification-and-bisect.md](references/01-scientific-hypothesis-falsification-and-bisect.md) | Competing hypotheses (`>= 2`), symptom vs root cause, automated `git bisect run`, delta debugging, `debug_hypothesis_gate.py` | Starting any non-trivial bug triage, post-commit regression, or misleading stack trace |
| [02-runtime-cpu-memory-and-event-loop-forensics.md](references/02-runtime-cpu-memory-and-event-loop-forensics.md) | Event-loop lag, CPU flamegraphs (`--cpu-prof`/`py-spy`/`pprof`), ReDoS, 3-snapshot heap diffs, native RSS & FD leaks | Diagnosing freezes, silent latency spikes, OOMKills, or growing memory with no stack trace |
| [03-deadlocks-race-conditions-and-network-hangs.md](references/03-deadlocks-race-conditions-and-network-hangs.md) | `pg_blocking_pids`, ascending-ID lock ordering, check-then-act races, pool self-deadlocks, local barriers, missing HTTP timeouts | Fixing DB deadlocks (`40P01`/1213), double execution, pool starvation, or hanging outbound requests |
| [04-flaky-tests-environment-drift-and-minimal-repro.md](references/04-flaky-tests-environment-drift-and-minimal-repro.md) | 8-axis env drift diff (runtime, lockfile, casing, `TZ`, Nginx proxy, RLS role, limits, `Boolean("false")`), redacted env fingerprinting | Resolving "works on my machine" CI/staging bugs or intermittent flaky test failures |
| [methodologies/SCIENTIFIC-DEBUGGING-AND-FAULT-TREES.md](methodologies/SCIENTIFIC-DEBUGGING-AND-FAULT-TREES.md) | Formal fault-tree & causal elimination methodology | Structuring complex multi-subsystem fault trees |
| [playbooks/DEBUG-REPORT-AND-REPRO-TEMPLATE.md](playbooks/DEBUG-REPORT-AND-REPRO-TEMPLATE.md) | Canonical `debug-report.md` & reproduction artifact template | Writing auditable root-cause debug handoff reports |
| [evaluations.md](evaluations.md) | Graded specialist evaluation scenarios (`DBG-EVAL-01..07`) | Auditing hypothesis discipline, forensics rigor, secret redaction, and `L0`/`L1` scope |

---

## 1. Preconditions, Permissions & Failure Handling
- **Default Access (`L0` / `L1`):** Read-only inspection (`read_repository`, `L0`) and bounded local reproduction tests (`L1_SAFE_VERIFICATION`). Never mutate production DBs/containers, run unapproved `L3` stress tests, or expose secrets/DSNs/PII in logs or `debug-report.md`.
- **Missing Evidence Rule:** If logs, stack traces, or environment reproduction are unavailable, mark missing evidence explicitly and propose safe instrumentation rather than guessing root cause from a single coincidental error line.
- **No Band-Aid Suppression:** Never silence a bug with `?.amount ?? 0`, empty `catch {}`, `sleep(3000)`, or `setMaxListeners(0)`.

---

## 2. 8-Step Scientific Debugging Playbook
Read [`methodologies/SCIENTIFIC-DEBUGGING-AND-FAULT-TREES.md`](methodologies/SCIENTIFIC-DEBUGGING-AND-FAULT-TREES.md) and [`playbooks/DEBUG-REPORT-AND-REPRO-TEMPLATE.md`](playbooks/DEBUG-REPORT-AND-REPRO-TEMPLATE.md) when executing complex diagnosis:
1. **Capture Symptom & Scope:** Expected vs actual behavior, severity, first occurrence, affected env/version.
2. **Build Redacted Timeline:** Correlate logs, W3C `traceparent` / `requestId`, commits (`git bisect`), and env drift; redact tokens/DSNs/PII.
3. **Rank Testable Hypotheses (`>= 2`):** Pair each hypothesis with explicit **disconfirming observations** and safe probes (never stop at the first plausible log line).
4. **Minimal Isolated Reproduction:** Create a minimal deterministic test or concurrency barrier fixture reproducing the failure (`FAIL` exit code != `0`).
5. **Pinpoint Minimal Root Cause:** Separate symptom, contributing factor, and causal mechanism using targeted instrumentation, flamegraphs, lock graphs, or bisect.
6. **Failing-Before Regression Test:** Record red-before run proving the test catches the exact bug.
7. **Minimal Behavior-Preserving Fix:** Apply smallest consistent change; execute targeted + adjacent regression suites (`PASS` exit code == `0`).
8. **Report & Recurrence Prevention:** Emit `debug-report.md` using the shared evidence envelope (`PASS | FAIL | NOT_RUN | BLOCKED`) and validate via `debug_hypothesis_gate.py`.

---

## 3. Deterministic Evidence Gate & Execution Boundaries (`L0`–`L4`)
- **Must-Reject Condition:** Any report claiming root cause from a single coincidental log line, repeating symptom as root cause, leaking unredacted credentials/DSNs, or missing failing-before evidence is **BLOCKED** by `debug_hypothesis_gate.py`.
- Log/config/code diagnosis is `L0_READ_ONLY`; minimal local reproduction tests are bounded `L1_SAFE_VERIFICATION`. Debugging NEVER authorizes `L3` stress/load testing (`/shadow-perf`) or `L4` staging/production mutations without explicit 7-part approval (`shadow-monarch/scripts/execution_approval_gate.py`).

```powershell
python "shadow-debug/scripts/debug_hypothesis_gate.py" --self-test
python "shadow-debug/scripts/debug_hypothesis_gate.py" --validate-report path/to/debug-report.json
python -m unittest discover -s shadow-debug/tests -v
```
