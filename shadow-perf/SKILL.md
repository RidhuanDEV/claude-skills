---
name: shadow-perf
description: "Pre-UAT Performance & Load Testing Gate. Use ONLY when entering the Pre-UAT/Staging performance gate or when explicitly asked for k6 load/stress/spike testing or SQL EXPLAIN ANALYZE profiling. Do NOT use automatically during feature coding."
---

# Shadow Perf (`/shadow-perf`) — Pre-UAT Load Testing (`k6`) & Bottleneck Profiler

> [!IMPORTANT]
> **STRICT EXECUTION GATE (PRE-UAT ONLY)**:
> Do **NOT** trigger `/shadow-perf` automatically while developing/coding features (`during` mode).
> Execute `/shadow-perf` **ONLY** when:
> 1. Feature development is complete and the system enters the **Pre-UAT / Staging Readiness Gate**, OR
> 2. The **Monarch** explicitly invokes `/shadow-perf` or asks for load testing / performance profiling.

---

## 1. Intake and contract selection

Establish the business journey, decision owner, timing, traffic shape and environment. Inspect prior performance reports, existing scripts, project generator, workload fixtures and SLOs. Ask the API owner for the authoritative resolved contract and its revision. A generated spec supplied as input is read-only. Keep any hand-maintained scripts and thresholds intact. A request to investigate a slow page usually starts with a saved trace; identify whether the elapsed time is in the browser, generator, network, application or database before proposing a benchmark.

## 2. Offline journey compiler

Use [the scaffold CLI](scripts/openapi_to_k6_scaffold.mjs) from an installed skill or the checkout. A plain inventory enumerates contract operations and produces inert draft files in a new output directory. An explicit journey supplies ordered operations, exact documented success statuses, synthetic JSON request bodies, path values and captures. JSON works without dependencies. YAML uses the existing service or repository YAML parser. Resolve modular references through the project workflow first. Requests with authentication or required query, header or cookie parameters require a project-owned adapter; the compiler rejects those selections.

For POST /orders and GET /orders/{id}, a fixture can be:

```json
{
  "steps": [
    {"operation":"POST /orders","expect":201,"body":{"label":"synthetic"},"capture":{"name":"created","field":"id"}},
    {"operation":"GET /orders/{id}","expect":200,"path":{"id":"$created"}}
  ],
  "mock": [
    {"method":"POST","path":"/orders","status":201,"response":{"id":"A-17"}},
    {"method":"GET","path":"/orders/A-17","status":200}
  ]
}
```

From the repository root:

```powershell
node shadow-perf/scripts/openapi_to_k6_scaffold.mjs --spec api.json --journey fixture.json --dry-run
node shadow-perf/scripts/openapi_to_k6_scaffold.mjs --spec api.json --journey fixture.json --out tests/perf-candidate
node --test shadow-perf/tests/scaffold.test.mjs
```

Dry-run replays local mock exchanges in memory and writes no files. Generation first checks the replay, then creates three familiar profile filenames without overwriting prior work. Each template starts at one iteration; its name describes the intended later profile. Generated scripts require an explicit loopback BASE_URL, matching APPROVED_PROFILE and disable redirects. They do not derive any target or credential from the specification. Human approval remains a separate precondition for traffic. Confirm that paths, query filters, response payloads, tenant authorization and fixture cleanup work in the actual service before claiming workload coverage.

## 3. Plan the experiment

- Derive the journey mix from representative traffic or named hypotheses. Choose an arrival-rate model for independent arrivals; choose concurrency for interactive users with think time. For each journey estimate request volume as iterations × steps plus modeled retries. Include setup, teardown, service quotas and data retention in cost bounds.
- Pin the service revision, fixture version, environment, workload mode, warm-up/discard interval, duration, cache state, observer and stop criteria. Report per-operation status contracts, latency percentiles, errors, retries and offered/achieved rate. Determine needed repetitions from run variability and uncertainty in the decision.
- For writes, agree on synthetic identity, unique data per run, compensation for partial failure and cleanup ownership. When authentication is required, obtain short-lived test credentials through the established adapter and keep secrets out of templates, traces and source control.
- For a database, begin with existing query telemetry or read-only plans. EXPLAIN ANALYZE executes its statement; inspect side effects, environment and authorization first. Compare cardinality estimates, distribution, locks, I/O and write amplification before suggesting an index. [SQL and runtime profiling](references/SQL-AND-RUNTIME-PROFILING.md)
- Separate planning and generation from load execution. Before any load/stress run, get the scope-specific L3 approval and L4 approval where applicable under the existing protocol. Confirm target, resource budget, stop signal and rollback owner. [k6 workflow patterns](references/K6-OPENAPI-PATTERNS.md)

## 4. Interpret stored evidence

Run `node shadow-perf/scripts/diagnose_window.mjs window.json` on a saved, aligned measurement window. Supply ISO UTC start/end, offered targetRps, achievedRps, generator and service CPU percentages, client and server p95 milliseconds, and pre-agreed limits {cpuPct, minDeliveryRatio, p95Ms}. Confirm metrics are drawn from the same warm-up policy, interval, workload and route/cohort before invoking. The helper identifies signals consistent with generator pressure, service pressure, mixed pressure or unattributed degradation. Missing measurements return INSUFFICIENT_EVIDENCE. CPU and latency alone cannot establish root cause: sample queueing, event-loop lag, network or connection limits as relevant. Hand observed evidence and the next discriminating experiment to the service/operations owner. Sign-off requires actual workload and recovery evidence from an approved environment.
