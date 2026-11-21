# Graceful Degradation, Bulkheads & Ephemeral Restore Drills

> Use this playbook when isolating resource pools via Bulkheads, designing stale-cache/feature-shedding degradation, or proving RPO/RTO via automated ephemeral backup restore drills.

## 1. Core Concepts
Resilience treats failure of non-critical dependencies as expected runtime state rather than a total outage:
- **Bulkhead Isolation:** Separate execution pools/semaphores ensure slow PDF exports, analytics queries, or upstream LLM outages fail boundedly (`503` fast-fail) without exhausting connections needed by checkout or authentication.
- **Unverified Backups Don't Exist:** Dump exit code `0` proves nothing until automated restoration into an isolated ephemeral container replays transaction logs / UU PDP erasure tombstones and meets agreed RPO & RTO objectives.

## 2. Technical Rules & Decision Matrix

| Failure Mode | Resilience Pattern | Verification / Objective |
| :--- | :--- | :--- |
| Slow exports / AI workers starving core API | **Bulkhead Concurrency Semaphore + Separate DB Pool** | Bounded active slots + queue cap; fast fail `503` + `Retry-After` |
| Downstream catalog/config service outage | **Stale-Cache Fallback (`stale-if-error`) + Shed Optional UI** | Serve last known valid snapshot cleanly tagged `stale: true`; degrade non-critical widgets |
| Database corruption / ransomware / accidental drop | **Automated Ephemeral Restore Drill + Tombstone Replay** | Measure real RTO/RPO timestamps via `scripts/drill_evidence.py`; zero Docker leaks |
| Queue poison / broker disconnect recovery | **Staging-Only Fault Injection + Bounded DLQ Replay** | Verify rate-limited replay does not overload primary DB pool |

## 3. Implementation Examples

### Strict-TS Bulkhead Concurrency Semaphore (Fast-Fail Saturation Guard)
```ts
export class BulkheadRejectedError extends Error {
  public constructor(bucket: string, limit: number) {
    super(`BULKHEAD_SATURATED: pool '${bucket}' reached limit (${limit})`);
  }
}

export class BulkheadSemaphore {
  private active = 0;

  public constructor(
    private readonly name: string,
    private readonly maxConcurrent: number,
  ) {}

  public async run<T>(task: () => Promise<T>): Promise<T> {
    if (this.active >= this.maxConcurrent) {
      throw new BulkheadRejectedError(this.name, this.maxConcurrent);
    }
    this.active += 1;
    try {
      return await task();
    } finally {
      this.active -= 1;
    }
  }
}
```

### Ephemeral Restore Drill & Leak-Proof Cleanup Pattern (`drill_evidence.py`)
```powershell
$containerName = "restore-drill-pg-test"
try {
  docker run -d --rm --name $containerName --label shadow.ephemeral=true `
    -e POSTGRES_PASSWORD=drill_only_temp_pw postgres:16-alpine
  if ($LASTEXITCODE -ne 0) { throw "Failed to start ephemeral restore container" }

  # Wait ready, restore dump artifact into isolated DB, replay UU PDP erasure_tombstones,
  # verify critical table counts & workflow query, and record ISO timestamps for drill_evidence.py
  python "shadow-resilience/scripts/drill_evidence.py" drill_receipt.json
} finally {
  docker rm -f -v $containerName 2>$null | Out-Null
}
```

## 4. Best Practices
- Reconcile `erasure_tombstones` immediately after any database snapshot restore so deleted user PII (UU PDP / GDPR) never silently resurrects from older backups.
- Keep critical user paths (auth, health, core payments) on physically or logically separate connection pools from heavy BI exports and webhook fan-out workers.

## 5. Anti-Patterns (`WRONG` vs `RIGHT`)
- **WRONG (Unbounded shared pool + trusting dump files blindly):** Letting heavy report downloads share the sole 20-connection DB pool, or marking RPO/RTO verified because `pg_dump` exited `0` months ago.
  **RIGHT:** Guard heavy endpoints with dedicated `BulkheadSemaphore` budgets and execute automated ephemeral restore drills recording real `disruption_at`, `recovered_checkpoint_at`, and `business_verified_at` receipts.
- **WRONG (Leaving temporary restore containers running after failed drills):** Creating orphan volumes/images that exhaust host disk (`shadow_gate.py --check-docker-leaks` flags these).
  **RIGHT:** Tag all temporary drill containers with `shadow.ephemeral=true` and wrap teardown in `try / finally` (`docker rm -f -v`).

## 6. Production Considerations
- **Blast Radius Boundary:** Fault/chaos injection against shared staging/production targets is `L3`/`L4` and requires explicit Monarch authorization; routine restore drills belong on isolated ephemeral fixtures.
