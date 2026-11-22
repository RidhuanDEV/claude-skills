---
name: shadow-perf
description: "Pre-UAT Performance & Load Testing Gate. Use ONLY when entering the Pre-UAT/Staging performance gate or when explicitly asked for k6 load/stress/spike testing, latency decomposition, SQL EXPLAIN profiling, or runtime CPU/memory profiling. Do NOT use automatically during feature coding."
---

# Shadow Perf (`/shadow-perf`) — Pre-UAT Load Testing (`k6`), Latency Diagnosis & Bottleneck Profiler

> [!IMPORTANT]
> **STRICT EXECUTION GATE (PRE-UAT ONLY & `L3`/`L4` APPROVAL):**
> Do **NOT** trigger `/shadow-perf` automatically while developing/coding features (`during` mode).
> Execute `/shadow-perf` **ONLY** when:
> 1. Feature development is complete and the system enters the **Pre-UAT / Staging Readiness Gate**, OR
> 2. The **Monarch** explicitly invokes `/shadow-perf` or asks for load testing / performance profiling.
> Separate planning and offline dry-run compilation (`L0`/`L1`) from live load execution — **ALWAYS** obtain explicit scope-specific **`L3` approval** (and **`L4` approval** for shared/live environments) before generating load traffic.

- **Owner:** Pre-UAT workload modeling & k6 journey compilation (`openapi_to_k6_scaffold.mjs`), stored-window pressure diagnosis (`diagnose_window.mjs`), multi-stage latency decomposition (API & RAG TTFT), safe SQL query plan & pool bottleneck profiling, and runtime CPU/memory/capacity sizing.
- **Boundaries:** Continuous production SLO alerting & tracing (`shadow-observe`), reversible DDL/index migrations (`shadow-db`/`shadow-data`), automated unit/integration tests (`shadow-test`), and multi-tier caching design (`shadow-cache`).

## Reference Guide

Load ONLY the 1–2 modular playbooks needed for the active performance subtask:

| Module | Topic | Load When |
| :--- | :--- | :--- |
| [01-workload-modeling-and-k6-journeys.md](references/01-workload-modeling-and-k6-journeys.md) | Arrival-rate vs closed-loop models, smoke/load/spike/soak, `openapi_to_k6_scaffold.mjs`, synthetic fixtures & `L3`/`L4` safety | Designing a Pre-UAT k6 test plan, compiling journeys from OpenAPI, preventing coordinated omission |
| [02-latency-decomposition-and-window-diagnosis.md](references/02-latency-decomposition-and-window-diagnosis.md) | `diagnose_window.mjs` (generator vs service vs mixed), percentile integrity (never average p95), warm-up discard, RAG TTFT waterfall | Interpreting saved load-test windows, isolating generator bottlenecks, or decomposing slow API/RAG stages |
| [03-sql-query-plan-and-pool-bottlenecks.md](references/03-sql-query-plan-and-pool-bottlenecks.md) | Static `EXPLAIN` vs `EXPLAIN ANALYZE` safety, buffer reads, tenant cardinality skew, sort spills, N+1, pool timeouts at low DB CPU | Profiling slow SQL queries, lock/pool exhaustion, or deep `OFFSET` pagination bottlenecks |
| [04-runtime-cpu-memory-profiling-and-capacity-sizing.md](references/04-runtime-cpu-memory-profiling-and-capacity-sizing.md) | Event-loop lag, 3-snapshot post-drain heap leak proof, CPU flamegraphs, CFS throttling, Little's Law replica sizing | Diagnosing Node/Python/Go/PHP CPU hotspots, proving memory leaks vs cache growth, or sizing capacity |
| [evaluations.md](evaluations.md) | Graded specialist evaluation scenarios (`PERF-EVAL-01..07`) | Auditing Pre-UAT gating, percentile rigor, SQL profiling safety, and generator-vs-service diagnosis |

---

## 1. Intake and Contract Selection

Establish the business journey, decision owner, timing, traffic shape, and environment. Inspect prior performance reports, existing scripts, project generator, workload fixtures, and SLOs. Ask the API owner for the authoritative resolved contract and its revision. A generated spec supplied as input is read-only. Keep any hand-maintained scripts and thresholds intact. A request to investigate a slow page or API usually starts with a saved trace; identify whether the elapsed time is in the browser, generator, network, application, reranker/upstream, or database before proposing a benchmark.

---

## 2. Offline Journey Compiler (`openapi_to_k6_scaffold.mjs`)

Use [the scaffold CLI](scripts/openapi_to_k6_scaffold.mjs) from an installed skill or checkout. A plain inventory enumerates contract operations and produces inert draft files in a new output directory. An explicit journey supplies ordered operations, exact documented success statuses, synthetic JSON request bodies, path values, and captures. JSON works without dependencies; YAML uses the existing service or repository YAML parser. Resolve modular references through the project workflow first. Requests with authentication or required query, header, or cookie parameters require a project-owned adapter; the compiler rejects those selections.

For `POST /orders` and `GET /orders/{id}`, a fixture can be:

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

Dry-run replays local mock exchanges in memory and writes no files. Generation first checks the replay, then creates three profile filenames without overwriting prior work. Each template starts at one iteration; its name describes the intended later profile. Generated scripts require an explicit loopback `BASE_URL`, matching `APPROVED_PROFILE`, and disable redirects. They do not derive any target or credential from the specification. Human approval remains a separate precondition for traffic. Confirm that paths, query filters, response payloads, tenant authorization, and fixture cleanup work in the actual service before claiming workload coverage.

---

## 3. Plan the Experiment & Profile Safely

- Derive the journey mix from representative traffic or named hypotheses. Choose an **arrival-rate** model for independent arrivals (prevents coordinated omission); choose **concurrency** for interactive users with think time. Estimate request volume as `iterations * steps * (1 + retryRate)`. Include setup, teardown, service quotas, and data retention in cost bounds.
- Pin the service revision, fixture version, environment, workload mode, warm-up/discard interval, duration, cache state, observer, and hard stop criteria. Report per-operation status contracts, latency percentiles (**never average p95s**), errors, retries, and offered vs achieved rate.
- For writes, agree on synthetic identity, unique data per run, compensation for partial failure, and cleanup ownership. Obtain short-lived test credentials through the established adapter and keep secrets out of templates, traces, and source control.
- For databases, begin with existing query telemetry or static read-only `EXPLAIN` plans. **`EXPLAIN ANALYZE` executes its statement** — inspect side effects, environment, and authorization first. Compare cardinality estimates across small & whale tenants, locks, buffer I/O, and write amplification before proposing an index.
- Before any load/stress run, get scope-specific **`L3` approval** (and **`L4`** where applicable). Confirm target, resource budget, stop signal, and rollback owner.

---

## 4. Interpret Stored Evidence (`diagnose_window.mjs`)

Run `node shadow-perf/scripts/diagnose_window.mjs window.json` on a saved, aligned measurement window. Supply ISO UTC start/end, offered `targetRps`, `achievedRps`, generator and service CPU percentages, client and server p95 milliseconds, and pre-agreed limits `{cpuPct, minDeliveryRatio, p95Ms}`. Confirm metrics are drawn from the same warm-up policy, interval, workload, and route/cohort before invoking. The helper classifies signals consistent with generator pressure, service pressure, mixed pressure, or unattributed degradation (`INSUFFICIENT_EVIDENCE` when measurements are missing). CPU and latency alone cannot establish root cause: sample queueing, pool waits, event-loop lag, network, or post-drain heap profiles as relevant. Hand observed evidence and the next discriminating experiment to the service/operations owner. Sign-off requires actual workload and recovery evidence from an approved environment.
