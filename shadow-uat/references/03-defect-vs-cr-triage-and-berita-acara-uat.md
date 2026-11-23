# 03. Severity-First Gate, Defect vs CR Triage & Formal `Berita Acara UAT`

## 1. Purpose & Activation Conditions
Use this playbook during active Staging UAT execution and close-out to triage client feedback cleanly into **Defects (Bugs)** versus **Change Requests (CRs)**, enforce the **Severity-First Release Gate**, and produce an auditable formal sign-off package (**Berita Acara UAT**) ready to unlock Production Release (`/shadow-release`) and Client Handover (`/shadow-handover`).

Activate this playbook when:
- Stakeholders log mixed issues during Staging UAT (some genuine bugs, some brand-new feature ideas).
- Deciding whether a Staging release candidate qualifies for `SIGN_OFF`, `CONDITIONAL_SIGN_OFF`, or `REJECT / REVISE`.
- Generating the formal `Berita Acara UAT` summary JSON/document for client signature (`/shadow-doc`).

## 2. Prerequisites
- Executed RTM rows and attached evidence artifacts from [`01-executable-rtm-and-business-scenarios.md`](01-executable-rtm-and-business-scenarios.md).
- Completed pre-client drift audit from [`02-intended-vs-implemented-drift-and-adversarial-uat.md`](02-intended-vs-implemented-drift-and-adversarial-uat.md).
- Signed PRD/SRS/KAK baseline so every triage verdict anchors to agreed scope rather than verbal memory.

## 3. Technical Principles & Constraints
1. **Severity-First Gate Overrides Numeric Pass Rates**: A `"98% pass rate"` NEVER authorizes Go-Live if even **one** open `Blocker` or `Critical` defect breaks authentication/authorization, tenant isolation, financial integrity, data durability, or a core P0 workflow. Zero open `Blocker`/`Critical` bugs is an absolute prerequisite.
2. **Strict Defect vs Change Request Separation**:
   - **Defect (Bug)**: Observed Staging behavior violates an agreed `FR-*`, `NFR-*`, `AC-*`, or security/data invariant -> Fix in Staging, add regression test (`/shadow-test`), and retest before sign-off.
   - **Change Request (CR)**: Client requests a new field, workflow, report, or rule NOT present in the signed baseline -> Log transparently in the CR Backlog with impact assessment and escalate contractual/schedule evaluation to **`/shadow-pmo`** so current-scope UAT sign-off is NOT held hostage indefinitely.
3. **Immutable Evidence Bundle & Checksum**: Package signed `Berita Acara UAT`, RTM table, Defect/CR Triage Log, and screenshot/HAR/batch evidence files with a SHA-256 checksum (`evidence_bundle_sha256`) so post-launch changes are cleanly distinguished from accepted baseline behavior.
4. **Explicit `CONDITIONAL_SIGN_OFF` Discipline**: Only permit conditional sign-off when `0` `Blocker`/`Critical` defects exist AND any `Minor`/`NOT TESTED` exception names an exact owner, mitigation, and target date approved in writing by the client approver.

## 4. Architecture & Implementation
### Severity Classification & Sign-Off Gate Policy
| Severity | Definition | Go-Live Impact | Mandatory Action Before Sign-Off |
| :--- | :--- | :--- | :--- |
| **Blocker** | Crash, data corruption, auth/RBAC/tenant bypass, or P0 workflow unusable | **HARD STOP (`REJECT`)** | Fix + regression test + full Staging retest |
| **Critical** | Severe functional/financial miscalculation, silent `E03` filter leak, deceptive `HTTP 202`, broken keyboard/a11y core path | **HARD STOP (`REJECT`)** | Fix + regression test + full Staging retest |
| **Major** | Significant workflow friction with documented temporary operational workaround | **Blocks full sign-off** unless explicitly waived as `CONDITIONAL_SIGN_OFF` | Fix before Go-Live or time-bounded waiver signed by Client Approver |
| **Minor** | Cosmetic alignment, typo, or non-blocking copy polish | Allowed with logged follow-up ticket | Track in post-launch Harwat backlog (`/shadow-maintain`) |

### Strict TypeScript Severity-First Gate Evaluator
```typescript
export type DefectSeverity = 'BLOCKER' | 'CRITICAL' | 'MAJOR' | 'MINOR';
export type TriageClassification = 'DEFECT' | 'CHANGE_REQUEST' | 'USER_EDUCATION';
export type UatGateDecision =
  | 'FULL_SIGN_OFF'
  | 'CONDITIONAL_SIGN_OFF'
  | 'REJECT_REVISE';

export interface OpenDefect {
  readonly id: string;
  readonly severity: DefectSeverity;
  readonly classification: TriageClassification;
  readonly waivedInWriting: boolean;
}

export interface UatGateSummary {
  readonly p0P1Total: number;
  readonly passed: number;
  readonly failed: number;
  readonly notTested: number;
  readonly openDefects: readonly OpenDefect[];
}

export function evaluateUatSignOffGate(
  summary: UatGateSummary,
): { readonly decision: UatGateDecision; readonly reasons: readonly string[] } {
  const reasons: string[] = [];
  const activeDefects = summary.openDefects.filter(
    (item) => item.classification === 'DEFECT',
  );
  const blockersOrCritical = activeDefects.filter(
    (item) => item.severity === 'BLOCKER' || item.severity === 'CRITICAL',
  );
  const unwaivedMajors = activeDefects.filter(
    (item) => item.severity === 'MAJOR' && !item.waivedInWriting,
  );

  if (blockersOrCritical.length > 0) {
    reasons.push(
      `Severity-first override: ${blockersOrCritical.length} open BLOCKER/CRITICAL defect(s) block sign-off regardless of pass percentage.`,
    );
  }
  if (summary.failed > 0) {
    reasons.push(`${summary.failed} P0/P1 RTM scenario(s) remain in FAIL status.`);
  }
  if (unwaivedMajors.length > 0) {
    reasons.push(`${unwaivedMajors.length} MAJOR defect(s) lack written client waiver.`);
  }
  if (reasons.length > 0) {
    return { decision: 'REJECT_REVISE', reasons };
  }

  if (summary.notTested > 0 || activeDefects.some((item) => item.severity === 'MAJOR')) {
    return {
      decision: 'CONDITIONAL_SIGN_OFF',
      reasons: [
        'Zero BLOCKER/CRITICAL defects, but NOT_TESTED rows or waived MAJOR items require explicit pilot/remediation clauses in Berita Acara UAT.',
      ],
    };
  }

  return {
    decision: 'FULL_SIGN_OFF',
    reasons: ['100% P0/P1 scenarios PASS with verified evidence and zero open BLOCKER/CRITICAL/MAJOR defects.'],
  };
}
```

### Formal `Berita Acara UAT` Structured Record
```json
{
  "release_candidate": "v1.4.0-rc2",
  "git_sha": "a1b2c3d4",
  "environment": "staging-uat",
  "p0_p1_total": 42,
  "passed": 41,
  "failed": 0,
  "not_tested": 1,
  "open_defects": { "blocker": 0, "critical": 0, "major": 0, "minor": 2 },
  "deferred_change_requests": ["CR-UAT-003"],
  "gate_decision": "CONDITIONAL_SIGN_OFF_PENDING_HSM_PILOT",
  "evidence_bundle_sha256": "<sha256-of-uat-evidence-archive>"
}
```

## 5. Platform / Vendor Variations
- **Government & Institutional Contracts (Indonesia)**: Generate formal **Berita Acara Pengujian Pengguna (BA-UAT)** via `/shadow-doc` (`templates/10_UAT.md` + `templates/11_BUG_LOG.md`) including signatory blocks for PPK / Client Project Owner, QA Lead, and Vendor Project Manager, enforcing `owner != approver`.
- **Continuous SaaS Releases**: Maintain lightweight release-candidate UAT sign-off records attached to GitHub Releases / Jira Release versions preserving RTM links and visual diff evidence.

## 6. Decision Matrix & Trade-Offs
| Client UAT Comment | Classification | Handling Path |
| :--- | :--- | :--- |
| *"Approver can click Approve on their own PO (`FR-PO-012` says forbidden)."* | **DEFECT (`CRITICAL`)** | Block sign-off -> fix -> add `403` regression test -> retest in Staging |
| *"Can we also add WhatsApp bot notifications and multi-currency FX conversion?"* | **CHANGE REQUEST (`CR`)** | Log in CR Register (`CR-UAT-*`) -> route to `/shadow-pmo` -> do NOT block current UAT scope |
| *"Where is the reset filter button? Oh, I see it on the right."* | **USER_EDUCATION / UX Polish (`MINOR`)** | Add to User Manual (`/shadow-handover`) & optional polish ticket; does not block release |

## 7. Real Production Scenario
**Context:** During Week 8 Staging UAT of an inventory system, client department heads logged 24 items: 1 critical stock-deduction race bug, 3 minor CSS glitches, and 20 brand-new feature requests (*"integrate TikTok Shop API"*, *"add AI demand forecasting"*). Without triage discipline, the project risked slipping 3 months with unpaid scope creep.
**Resolution:** Anchoring every item to the signed SRS (`FR-*`) separated the 1 `Critical` defect (fixed + regression tested in 1 day), logged 3 `Minor` tickets into monthly Harwat, and routed the 20 new features into a clean Phase 2 CR backlog via `/shadow-pmo`. Client leadership signed **Berita Acara UAT** on schedule with zero unresolved blockers.

## 8. Failure Modes & Edge Cases
- **WRONG (Approving Go-Live based on percentage alone):** Issuing *"PASS (97.6% — 41/42 passed)"* while the 1 failing scenario is a `Critical` cross-tenant IDOR or duplicate-debit bug.
  **RIGHT:** Trigger `REJECT_REVISE` immediately whenever any `BLOCKER` or `CRITICAL` defect remains open.
- **WRONG (Silently promising free CR implementation during UAT calls):** Telling testers *"Sure, we will add those 5 new dashboards before Go-Live"* without updating SRS or consulting `/shadow-pmo`.
  **RIGHT:** Record every out-of-scope request as a formal `CR` entry and escalate contractual impact to `/shadow-pmo`.

## 9. Testing & Verification
- Verify `evaluateUatSignOffGate` logic against boundary cases: 99% pass + 1 `CRITICAL` -> `REJECT_REVISE`; 0 blockers + 1 `NOT_TESTED` -> `CONDITIONAL_SIGN_OFF`; 100% pass + 0 blockers/majors -> `FULL_SIGN_OFF`.
- Validate final `UAT` and `RTM` documents via `shadow-doc/scripts/doc_scaffold.py validate --doc <UAT.json> --strict` before client submission.

## 10. Operational Considerations
- Hand signed `Berita Acara UAT` directly to `/shadow-release` (production rollout authorization) and `/shadow-handover` (`BAST` annex).
- Preserve all `Minor` waived defects into the initial `/shadow-maintain` Harwat backlog so nothing falls through the cracks post-launch.

## 11. Authoritative References
- **ISO/IEC/IEEE 29119-3:2021** — *Test Documentation (Test Completion Report & Incident/Defect Reports)*.
- **Shadow Doc Templates** — `shadow-doc/templates/10_UAT.md`, `11_BUG_LOG.md`, and `12_CHANGE_REQUEST.md`.

## 12. Limitations & When NOT to Use
- **Do NOT use** `/shadow-uat` to calculate Paid CR pricing, PERT schedules, or contractual arbitration — route to `/shadow-pmo`.
- **Do NOT use** `/shadow-uat` to execute production deployment or post-go-live `SEV1` incident response — route to `/shadow-release` and `/shadow-maintain`.
