# Production Incident Triage, Blameless RCA & Harwat Maintenance Playbook

> Use this playbook when triaging `SEV1`–`SEV4` production incidents, authoring blameless 5-Why / Fault-Tree postmortems, shipping surgical hotfixes with regression tests, or executing preventive Harwat/OMKT maintenance.

## 1. Core Concepts
Production incident response separates **immediate customer restoration** from **deep root-cause forensics**:
- **Restore Service Before Refactors:** During active outages (`SEV1`/`SEV2`), preserve diagnostic state (logs, metrics, heap snapshot if safe), stabilize traffic via the fastest reversible control (feature flag off, config revert, known-good rollback), and only then perform deep code surgery.
- **Systemic Blameless RCA:** Replace human blame ("engineer forgot X") with concrete control gaps (missing CI contract check, missing DB invariant, missing alert threshold) backed by time-bounded action items.

## 2. Technical Rules & Decision Matrix

| Severity | Customer Impact | Immediate Action Path | Follow-Up Gate |
| :--- | :--- | :--- | :--- |
| `SEV1` (Critical Outage / Data Risk) | Total outage, auth bypass, or financial/PII corruption | **Engage Incident Lead -> Preserve Evidence -> Flag Off / Rollback** | Mandatory blameless RCA (`< 48h`), permanent regression test + SLO alert |
| `SEV2` (Major Degradation) | Core workflow severely degraded or high `5xx` for cohort | **Contain Bad Cohort / Scale Pool / Targeted Rollback** | Blameless RCA, regression test reproducing failure BEFORE fix |
| `SEV3` (Scoped Bug + Workaround) | Non-blocking workflow defect with safe workaround | **Scoped Hotfix** (failing test first -> smallest surgical diff) | Verify clean unit/integration suite before merge |
| `SEV4` / Monthly **Harwat / OMKT** | Preventive SLA / cosmetic / certificate / query hygiene | **Corrective + Adaptive + Perfective Cycle** | Check TLS expiry, dependency advisories, slow query plans (`/shadow-db`), restore drill |

## 3. Implementation Examples

### Blameless 5-Why / Fault-Tree Postmortem Template
```markdown
## Postmortem: INC-2026-041 — Checkout Webhook Timeout Spike (SEV2)
- **Window (UTC):** 2026-04-12 03:14 – 03:38 (24m) | **Impact:** 4.2% checkout confirmations delayed `> 60s`
- **Immediate Mitigation:** Enabled worker bulkhead cap & drained backlog cleanly at 03:38.

### Causal Chain (5-Whys)
1. **Why did confirmations stall?** Checkout DB pool saturated (`100%` active for 24m).
2. **Why did the pool saturate?** Export batch worker shared the same PostgreSQL pool during promo surge.
3. **Why wasn't saturation prevented?** Bulkhead isolation and separate worker read-replica pool were absent.
4. **Why wasn't it detected pre-incident?** Staging load probe (`shadow-perf`) skipped concurrent export + checkout mix.

### Corrective & Preventive Actions
| ID | Action | Owner | Verification Proof | Due |
| :--- | :--- | :--- | :--- | :--- |
| ACT-1 | Isolate worker DB pool + `BulkheadSemaphore(4)` | Backend | Unit test + staging concurrency check | +3d |
| ACT-2 | Add regression test + burn-rate alert on pool wait `> 250ms` | SRE | Alert dry-run + green CI suite | +5d |
```

## 4. Best Practices
- Enforce the **Hotfix Minimalism Rule:** every hotfix commit MUST contain (1) a regression test reproducing the exact failure mode BEFORE the fix, and (2) the smallest patch strictly addressing the verified root cause.
- Track recurring `SEV3` tickets or slow SQL regressions in monthly Harwat backlog reviews (`/shadow-db` index inspection + `npm/pip audit` + monthly `/shadow-resilience` restore drill).

## 5. Anti-Patterns (`WRONG` vs `RIGHT`)
- **WRONG (Restarting pods before capturing volatile state & fixing blindly):** Immediately bouncing containers or adding unrelated cleanup refactors inside a `SEV1` hotfix PR (destroys forensic heap/logs and multiplies regression blast radius).
  **RIGHT:** Capture recent logs/thread dumps first, mitigate safely (flag off / rollback), reproduce root cause in an isolated test, and ship a surgical patch.
- **WRONG ("Human error" as final RCA cause):** Concluding "dev missed a null check" with action item "be more careful next time".
  **RIGHT:** Identify why automation allowed the failure (`strictNullChecks` disabled, missing negative API test, unguarded queue retry) and ship structural prevention.

## 6. Production Considerations
- **Post-Hotfix Hygiene:** Verify whether an emergency hotfix bypassed standard release checks and backfill missing contract/RTM updates (`shadow-uat` / `shadow-compat`) immediately once stability returns.
- **Access & Audit Guardrail:** Never pull unmasked live production PII dumps to local machines while triaging — obtain anonymized fixtures or read-only authorized telemetry (`shadow-privacy`).
