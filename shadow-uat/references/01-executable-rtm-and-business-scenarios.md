# 01. Executable Requirement Traceability Matrix (RTM) & Staging UAT Scenarios

## 1. Purpose & Activation Conditions
Use this playbook when preparing Staging User Acceptance Testing (UAT), constructing an auditable Requirement Traceability Matrix (`RTM`), or authoring business-language test scenarios for client and QA testers. Automated unit tests prove the code matches developer expectations; Staging UAT proves the candidate release satisfies the agreed business requirements (`FR-*`) on realistic, anonymized data before Production Go-Live (`/shadow-release`).

Activate this playbook when:
- Translating locked `FR-*` and `AC-*` requirements from `/shadow-discovery` into Staging UAT scenarios (`UAT-*`).
- Auditing whether `100%` of `P0` and `P1` requirements have executable test steps, negative probes, and attached evidence artifacts.
- Preparing Staging data fixtures and client-facing UAT execution workbooks (compatible with `/shadow-doc` `.docx` and `.xlsx` export).

## 2. Prerequisites
- Locked PRD/SRS (`FR-*`, `NFR-*`, `AC-*`) from `/shadow-discovery` and implemented feature specs (`FEATURE-DESIGN.md`) from `/shadow-design`.
- Staging release candidate deployed with version/commit SHA pinned and anonymized/synthetic seed data provisioned (ZERO unmasked production PII!).
- Existing automated regression test suite passing locally and in CI (`/shadow-test`).

## 3. Technical Principles & Constraints
1. **Staging-First Safe Delivery Sequence**: Always execute UAT on **Staging** first -> run Defect Fix & Retest loop -> secure Staging UAT sign-off -> execute `/shadow-release` to Production -> run non-destructive Production smoke verification. Never treat Production as the primary UAT playground.
2. **100% P0/P1 Bidirectional Traceability**: Every P0 and P1 requirement MUST trace cleanly across `FR-ID -> US-ID -> FLOW-ID -> SCR/STATE-ID -> UAT-ID -> TEST-ID -> Evidence Artifact`. Any P0/P1 row without a mapped scenario is an automatic UAT readiness blocker.
3. **Business Operational Language (Not Code Jargon)**: Write UAT steps so business operators and client stakeholders can execute and judge pass/fail without reading TypeScript or SQL: concrete test role, exact login persona, concrete input values, expected screen display, and expected business outcome (status change, generated document, or notification).
4. **Honest Evidence Labeling (`PASS | FAIL | BLOCKED | NOT TESTED`)**: Every RTM row MUST record exact observed status backed by a verifiable artifact (screenshot, HAR/HTTP receipt, batch reconciliation log, or exported document). Never mark an unexecuted manual scenario as `PASS`; label skipped checks `NOT TESTED` with the explicit reason.
5. **Anonymized Synthetic Staging Fixtures**: Seed Staging with realistic volume, edge-case Unicode names, `Asia/Jakarta` timezone boundaries, and synthetically valid Indonesian IDs (`NIK`/`NPWP` synthetic generators) — strictly prohibit copying raw production PII tables into Staging (`/shadow-privacy`).

## 4. Architecture & Implementation
### Executable RTM Table Standard (`shadow-doc` `.docx` / `.xlsx` Compatible)
| RTM-ID | FR-ID | Role / Actor | Endpoint or UI Flow | Positive & Negative Test Probes | Evidence Artifact | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `UAT-PO-001` | `FR-PO-012` | `Finance Approver` | Purchase Order Approval (`POST /orders/:id/approve`) | Happy approve (`200`), self-approve (`403`), blank reject reason (`422`), stale `ETag` (`409`) | `evidence/uat-po-001-approve.har` | `PASS` |
| `UAT-PO-002` | `FR-PO-015` | `Operator` | Filtered Ledger (`GET /orders?status=PAID&from=...`) | Verify returned rows exclude `DRAFT`/`PENDING`; empty filter reset at `375px` | `evidence/uat-po-002-filter-375px.png` | `PASS` |
| `UAT-SET-003` | `FR-SET-018` | `Batch Worker` | Nightly Bank Settlement Reconciliation | Seed duplicate webhook + timeout; verify single ledger debit & balanced batch receipt | `evidence/uat-set-003-reconcile.json` | `PASS` |
| `UAT-HSM-004` | `FR-SIG-021` | `Compliance Officer` | Physical HSM Smartcard Document Signing | Physical USB smartcard reader unavailable in cloud Staging | *(Pending pilot lab hardware)* | `NOT TESTED` |

### Typed RTM Completeness & Evidence Auditor
```typescript
export type UatStatus = 'PASS' | 'FAIL' | 'BLOCKED' | 'NOT_TESTED';
export type ReqPriority = 'P0' | 'P1' | 'P2';

export interface RtmRow {
  readonly uatId: string;
  readonly frId: string;
  readonly priority: ReqPriority;
  readonly hasNegativeProbe: boolean;
  readonly evidencePath: string | null;
  readonly status: UatStatus;
}

export function auditRtmCoverage(
  rows: readonly RtmRow[],
): { readonly readyForSignOff: boolean; readonly issues: readonly string[] } {
  const issues: string[] = [];

  for (const row of rows) {
    if (row.priority === 'P2') {
      continue;
    }
    if (row.status === 'PASS' && (row.evidencePath === null || row.evidencePath.trim() === '')) {
      issues.push(`${row.uatId} (${row.frId}): marked PASS without evidence artifact.`);
    }
    if (!row.hasNegativeProbe) {
      issues.push(`${row.uatId} (${row.frId}): missing negative/boundary probe.`);
    }
    if (row.status === 'FAIL' || row.status === 'BLOCKED') {
      issues.push(`${row.uatId} (${row.frId}): P0/P1 scenario is ${row.status}.`);
    }
  }

  return {
    readyForSignOff: issues.length === 0,
    issues,
  };
}
```

## 5. Platform / Vendor Variations
- **Web SaaS & Enterprise Portals**: Attach desktop (`1440px`) + mobile (`375px`) screenshots, HAR traces for negative HTTP assertions, and downloadable PDF/CSV export samples.
- **Batch-Only / Headless Back-Office Pipelines**: When no interactive UI exists, attach (1) synthetic input batch fixture checksum, (2) execution completion receipt (timestamp, exit code, row counts), and (3) reconciled output summary proving zero dropped or double-counted records (`test_batch_uat_and_param_drift.py`).
- **Indonesian Government / Regulated Projects**: Author client-facing UAT scenarios in formal Bahasa Indonesia (`DITERIMA` / `REVISI`) with tester signature columns so evidence folds directly into `templates/08_RTM.md` and `templates/10_UAT.md` in `/shadow-doc`.

## 6. Decision Matrix & Trade-Offs
| UAT Scenario Scope | Required Evidence | Sign-Off Impact if Unexecuted |
| :--- | :--- | :--- |
| **Interactive UI + API P0 Flow** | Role login proof + screenshot (`1440px` & `375px`) + negative status proof (`403`/`422`/`409`) | Blocks Go-Live unless formally deferred |
| **Headless Batch / Reconciliation Job** | Input manifest + run completion receipt + reconciled balance totals | Blocks Go-Live for financial/ledger workflows |
| **External Hardware / Third-Party Live Rail** | Staging sandbox receipt; if physically absent in Staging, mark `NOT TESTED` + explicit Pilot Gate | Requires Conditional Sign-Off naming exact pilot verification owner |

## 7. Real Production Scenario
**Context:** A payroll portal ran Staging UAT using only 15 happy-path scripts written by backend developers (*"POST /payroll/run returns 200"*). Client HR testers signed off without testing rejected bank accounts or month-end holiday cutoff dates.
**Failure:** On the first live payday, 14 employees with inactive bank accounts caused the batch job to abort midway after paying half the company, with no idempotent resume record.
**Fix:** Upgrading the RTM to require negative/boundary probes per P0 row (`UAT-PAY-004: invalid bank account quarantine + safe partial re-run`) plus reconciled batch output evidence caught partial-failure handling bugs in Staging before subsequent releases.

## 8. Failure Modes & Edge Cases
- **WRONG (Marking skipped checks as `PASS` to look "100% green"):** Hardware token or bank live rail was not tested in Staging, yet the RTM table lists `PASS` with `evidence: N/A`.
  **RIGHT:** Record `NOT TESTED` explicitly, document the environmental constraint, and issue a `CONDITIONAL_SIGN_OFF` tied to a controlled pilot check.
- **WRONG (Copying raw production PII into Staging for UAT realism):** Running `pg_dump prod | psql staging` exposing real customer `NIK`, salaries, and emails to external QA contractors.
  **RIGHT:** Seed Staging exclusively with deterministic anonymized/synthetic fixtures (`/shadow-data` + `/shadow-privacy`).

## 9. Testing & Verification
- Execute `python -m unittest discover -s shadow-uat/tests -v` to verify batch UAT evidence rules and query-parameter drift assertions (`test_batch_uat_and_param_drift.py`).
- Audit the completed RTM table with `auditRtmCoverage` to confirm zero `PASS` rows lack evidence files and zero P0/P1 rows lack negative/boundary probes.

## 10. Operational Considerations
- Archive UAT evidence bundles alongside exact release candidate Git SHA and SHA-256 archive checksum so post-launch disputes can be compared against signed Staging acceptance proof.
- Freeze Staging schema/deployments during active client UAT test windows (deploy defect fixes in scheduled retest batches with clear release notes).

## 11. Authoritative References
- **ISO/IEC/IEEE 29119-2 / 29119-3** — *Software testing — Test processes and test documentation (Traceability & Acceptance Test Completion Report)*.
- **ISTQB CTFL v4.0** — *User Acceptance Testing & Defect Management Lifecycle*.
- **Shadow Doc Templates** — `shadow-doc/templates/08_RTM.md` & `shadow-doc/templates/10_UAT.md`.

## 12. Limitations & When NOT to Use
- **Do NOT use** Staging UAT to replace developer unit/integration testing (`/shadow-test`) or Pre-UAT k6 load/stress benchmarking (`/shadow-perf`).
- **Do NOT use** `/shadow-uat` to execute Production deployment or rollback automation — hand signed releases to `/shadow-release`.
