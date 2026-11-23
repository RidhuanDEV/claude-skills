# 03. Blameless RCA, CAPA Engineering & Monthly Harwat / OMKT Cycles

## 1. Purpose & Activation Conditions
Use this playbook after every `SEV1`/`P0` or `SEV2`/`P1` production incident to author a systemic **Blameless Postmortem (RCA)** and track verifiable **Corrective & Preventive Actions (CAPA)**, as well as to execute structured monthly **Pemeliharaan & Perawatan (Harwat / OMKT)** preventive maintenance cycles and SLA reports (`/shadow-doc`).

Activate this playbook when:
- Writing `docs/incidents/RCA-YYYY-MM-DD-<slug>.md` within `< 48` hours of stabilizing a `SEV1`/`SEV2` incident.
- Converting recurring production tickets into concrete systemic controls (CI checks, DB constraints, bulkheads, alerts, regression tests).
- Running the monthly Corrective, Adaptive, and Perfective Harwat maintenance cycle and preparing the institutional **Laporan Harwat / SLA** deliverable.

## 2. Prerequisites
- Stabilized incident timeline (UTC and `Asia/Jakarta` WIB), customer impact metrics, error budget consumed (`/shadow-observe`), and hotfix commit SHA from [`01-severity-sla-triage-and-containment.md`](01-severity-sla-triage-and-containment.md) and [`02-surgical-hotfix-and-regression-gates.md`](02-surgical-hotfix-and-regression-gates.md).
- Read-only telemetry snapshots for monthly Harwat health checks (TLS expiry dates, slow query reports from `/shadow-db`, dependency audit reports from `/shadow-supplychain`, and latest restore drill results from `/shadow-resilience`).

## 3. Technical Principles & Constraints
1. **Systemic Blamelessness Over Individual Fault**: Never terminate a 5-Why causal chain at *"Engineer forgot to check null"* or *"Operator ran the wrong command"*. Assume competent engineers acting in good faith and ask: *"Which missing automated guardrail, schema constraint, CI check, or runbook control allowed this failure to reach Production?"*
2. **Evidence-Grounded Timelines & Impact**: Every RCA timestamp (`Detection`, `Ack`, `Escalation`, `Mitigation`, `Recovery`) and impact metric (`affected_requests`, `affected_tenants`, `error_budget_burn`) MUST cite real telemetry or incident logs (`[EVIDENCE]`). Mark unmeasured figures explicitly as `UNMEASURED` — never fabricate percentages or timestamps (`/shadow-doc` Golden Law 2).
3. **Verifiable CAPA Action Items**: Every Corrective or Preventive Action MUST declare: (a) concrete artifact/control (`CI check`, `DB constraint`, `burn-rate alert`, `bulkhead pool`), (b) single accountable owner, (c) measurable verification proof (`unit test`, `alert dry-run`, `restore drill`), and (d) explicit due date. Vague actions like *"be more careful"* or *"remind team in standup"* are forbidden.
4. **Four ISO/IEC/IEEE 14764 Maintenance Pillars (Monthly Harwat / OMKT)**:
   - **Corrective**: Close reported defects with commit SHA, regression test, and before/after evidence.
   - **Adaptive**: Apply OS/runtime/SDK patches, renew expiring TLS certificates (`> 30d` runway), adapt to third-party API deprecations (`/shadow-compat`).
   - **Perfective**: Tune slow SQL plans (`/shadow-db`), rotate/prune storage & logs, update vulnerable dependencies (`npm/pip/composer audit`), and reduce recurring alert noise.
   - **Preventive**: Execute monthly automated backup restore drills verifying RPO/RTO (`/shadow-resilience`) and check DR runbooks.

## 4. Architecture & Implementation
### Blameless 5-Why / Fault-Tree RCA Template (`shadow-doc` `14_INCIDENT` + `15_CAPA` Ready)
```markdown
## Postmortem: INC-2026-041 — Checkout Webhook Confirmation Timeout Spike (SEV2)
- **Window (UTC / WIB):** 2026-04-12 03:14–03:38 UTC (10:14–10:38 WIB, duration 24m)
- **Customer Impact:** 4.2% of checkout confirmations delayed > 60s (184 orders); 0 financial double-charges verified via ledger reconciliation.
- **SLO Error Budget Burned:** 18.5% of 30-day availability budget.
- **Immediate Mitigation:** Enabled worker bulkhead cap (`MAX_CONCURRENT_EXPORTS=4`) at 03:32 UTC; queue drained cleanly at 03:38 UTC.

### Causal Chain (5-Whys — Systemic Controls Focus)
1. **Why did webhook confirmations time out?** Primary PostgreSQL connection pool saturated at 100% active connections for 24 minutes.
2. **Why did the pool saturate?** Month-end CSV export workers shared the primary transactional connection pool during a promotional traffic surge.
3. **Why did export workers share the transactional pool?** No bulkhead pool separation or read-replica routing was enforced for background batch queries.
4. **Why wasn't saturation detected before launch?** Pre-UAT staging load profiles tested checkout traffic alone without concurrent export jobs.
5. **Why did alerting lag by 9 minutes?** Alert threshold watched only HTTP 5xx rate rather than DB pool wait latency (`> 250ms`).

### Corrective & Preventive Actions (CAPA)
| CAPA-ID | Type | Structural Action | Owner | Verification Proof | Due |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `CAPA-041-1` | Corrective | Isolate export worker pool to read replica + `BulkheadSemaphore(4)` | Backend Lead | Concurrency integration test + Staging pool metrics | +3d |
| `CAPA-041-2` | Preventive | Add Prometheus/OTel alert on DB pool wait `p95 > 250ms` for 2m | SRE | Synthetic alert dry-run firing to staging channel | +5d |
| `CAPA-041-3` | Preventive | Add concurrent checkout + export scenario to Pre-UAT k6 suite | QA / Perf | Updated k6 script committed (`[APPROVAL-REQUIRED: L3]` for run) | +7d |
```

### Strict TypeScript Blameless RCA & CAPA Quality Gate
```typescript
export interface CapaActionItem {
  readonly id: string;
  readonly action: string;
  readonly owner: string;
  readonly verificationProof: string;
  readonly dueDateIso: string;
}

const BLAME_OR_VAGUE_PATTERNS: readonly RegExp[] = [
  /\bhuman error\b/i,
  /\bbe more careful\b/i,
  /\bremind (?:the )?team\b/i,
  /\bdeveloper forgot\b/i,
];

export function auditCapaQuality(
  items: readonly CapaActionItem[],
): readonly string[] {
  const issues: string[] = [];
  if (items.length === 0) {
    return ['RCA must produce >= 1 structural CAPA action item.'];
  }
  for (const item of items) {
    if (item.owner.trim() === '' || item.verificationProof.trim() === '') {
      issues.push(`${item.id}: missing accountable owner or measurable verification proof.`);
    }
    for (const pattern of BLAME_OR_VAGUE_PATTERNS) {
      if (pattern.test(item.action)) {
        issues.push(`${item.id}: contains blame/vague wording ('${item.action}'); replace with a systemic control.`);
      }
    }
  }
  return issues;
}
```

## 5. Platform / Vendor Variations
- **Indonesian Institutional Harwat / OMKT Contracts**: Package monthly deliverables via `/shadow-doc` (`templates/14_INCIDENT.md`, `15_CAPA.md`, `19_MAINTENANCE.md`) showing SLA attainment %, ticket closure table (linked to commit SHAs & before/after evidence), TLS/backup health checks, and open CAPA status.
- **High-Velocity SaaS Teams**: Review open `SEV1`/`SEV2` CAPA items in weekly engineering operations standups; if an uncompleted `P0` CAPA slips past its due date, pause non-urgent feature work until systemic protection lands.

## 6. Decision Matrix & Trade-Offs
| Maintenance Activity | Cadence | Collaborating Skill | Evidence Artifact |
| :--- | :--- | :--- | :--- |
| **Blameless RCA + CAPA Review** | Within `< 48h` of `SEV1`/`SEV2` | `/shadow-observe`, `/shadow-debug`, `/shadow-doc` | `RCA-YYYY-MM-DD-*.md` + tracked CAPA tickets |
| **TLS, Dependency & CVE Hygiene** | Monthly (or urgent CVE `< 24h`) | `/shadow-supplychain`, `/shadow-sec`, `/shadow-ops` | Audit report + patched lockfile + test proof |
| **Slow Query & Index Tuning** | Monthly Harwat | `/shadow-db` | Before/after `EXPLAIN ANALYZE` + online index migration |
| **Backup Restore & RPO/RTO Drill** | Monthly Harwat | `/shadow-resilience` | Ephemeral restore drill report (zero leftover containers) |

## 7. Real Production Scenario
**Context:** A government tax portal suffered three nearly identical month-end outages over 6 months. Each previous incident report concluded *"Root cause: operator forgot to prune disk logs; Action: remind ops team."*
**Turnaround:** Switching to blameless systemic RCA uncovered the structural defects: missing `logrotate` size caps, no disk-utilization alert at `75%`, and unindexed audit-log exports filling `/tmp`. Shipping 3 verifiable CAPA items (automated log rotation, `75%`/`85%` alerts, and streaming export queries) eliminated disk outages for the entire next 18 months and earned `99.96%` SLA attainment on the monthly Harwat reports.

## 8. Failure Modes & Edge Cases
- **WRONG ("Human error" as root cause & "be more careful" as CAPA):** Writing *"Root cause: Junior dev forgot null check. Action: Remind devs to review PRs carefully."*
  **RIGHT:** Identify the missing structural safeguard (e.g., `strictNullChecks` disabled, missing negative API schema test, no canary alert) and ship a concrete verifiable engineering control.
- **WRONG (Monthly Harwat report listing "System Healthy" with zero evidence):** Submitting a monthly OMKT report claiming *"All backups OK, security patched"* without ever executing a restore drill or running dependency/TLS audits.
  **RIGHT:** Attach concrete evidence per pillar (commit SHAs, audit summaries, TLS expiry dates, slow-query stats, restore drill log) and label any skipped check explicitly `NOT_RUN`.

## 9. Testing & Verification
- Audit every drafted RCA/CAPA against `auditCapaQuality` (zero blame/vague strings, every item has owner + measurable verification proof + due date).
- Validate exported `INCIDENT`, `CAPA`, and `MAINTENANCE` reports with `shadow-doc/scripts/doc_scaffold.py validate --doc <report.json> --strict` before institutional submission.

## 10. Operational Considerations
- Track **CAPA Closure Rate** and **Repeat Incident Rate** across quarterly Harwat reviews: repeat incidents mean previous CAPAs addressed symptoms instead of root systemic controls.
- Separate **Out-of-Scope Enhancement Requests** raised during Harwat meetings from contractual Maintenance SLA tickets—escalate new feature enhancements to `/shadow-pmo`.

## 11. Authoritative References
- **ISO/IEC/IEEE 14764:2022** — *Software Life Cycle Processes — Maintenance (Corrective, Adaptive, Perfective, Preventive)*.
- **Google SRE Book** — *Postmortem Culture: Learning from Failure* (`https://sre.google/sre-book/postmortem-culture/`).
- **Shadow Doc Templates** — `shadow-doc/templates/14_INCIDENT.md`, `15_CAPA.md`, and `19_MAINTENANCE.md`.

## 12. Limitations & When NOT to Use
- **Do NOT use** `/shadow-maintain` to build brand-new greenfield software modules or negotiate Paid Change Requests — route to `/shadow-discovery` / `/shadow-plan` / `/shadow-pmo`.
- **Do NOT use** to run live backup restore drills directly without ephemeral isolation & cleanup — delegate restore drills to `/shadow-resilience`.
