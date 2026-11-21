# Requirement Traceability Matrix (RTM), Staging UAT & Sign-Off Gates

> Use this playbook when preparing Staging UAT test suites, auditing query/filter contracts (`E03` checks), triaging UAT defects, attaching verifiable evidence, or authoring client UAT Sign-Off (`Berita Acara UAT`).

## 1. Core Concepts
UAT bridges technical CI verification and business acceptance on Staging before Production Release:
- **Severity-First Gate:** A numeric "96% test pass rate" means nothing if 1 `Blocker` or `Critical` defect breaks authorization, financial correctness, or core workflow completion. Zero open `Blocker`/`Critical` bugs overrides any score threshold.
- **Honest Evidence Labeling:** Every RTM row reports exact observed outcome (`PASS`, `FAIL`, `BLOCKED`, or `NOT TESTED`) backed by concrete evidence artifacts — never collapse skipped manual checks into `PASS`.

## 2. Technical Rules & Decision Matrix

| UAT Check Type | Scope & Target | Sign-Off Verdict Rule |
| :--- | :--- | :--- |
| **RTM Functional Trace** | `100%` of P0/P1 requirements (`FR-ID -> US -> Endpoint/UI -> Evidence`) | Every P0/P1 row requires `PASS` + verified screenshot, HTTP trace, or batch receipt |
| **Query & Filter Contract Audit (`E03`)** | List endpoints, pagination, sort & search params | Assert `?status=...&from=...&to=...` genuinely filters returned IDs (catches silently ignored params) |
| **Negative & Role Boundary Suite** | Invalid input (`400`/`422`), unauth (`401`), cross-tenant/role (`403`/`404`), conflict (`409`) | Unauthorized user MUST fail closed with zero state mutation |
| **UI State & Mobile Parity** | Empty, Loading, Error, Denied + `375px` viewport & `200%` zoom | Intended-vs-Implemented drift audit zero regressions |

## 3. Implementation Examples

### Executable Requirement Traceability Matrix (RTM) & Defect Triage Format
| RTM-ID | FR-ID | Endpoint / UI Flow | Positive & Negative Test Probes | Evidence Artifact | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `UAT-001` | `FR-012` | Order Approval (`POST /orders/:id/approve`) | Happy approve (`200`), self-approve (`403`), stale version (`409`) | `evidence/uat-001-approve.har` | `PASS` |
| `UAT-002` | `FR-015` | Filtered Ledger (`GET /orders?status=PAID&q=inv`) | Verify response excludes `DRAFT`/`PENDING`; empty state at `375px` | `evidence/uat-002-filter-375px.png` | `PASS` |
| `UAT-003` | `FR-018` | Batch Settlement Reconciliation Job | Seed duplicate webhook + unknown bank timeout; verify single debit | `evidence/uat-003-batch-receipt.json` | `PASS` |
| `UAT-004` | `FR-021` | Manual HSM Smartcard Sign-Off Flow | Hardware token unavailable in Staging | *(Hardware reader absent in Staging)* | `NOT TESTED` |

### Staging UAT Sign-Off Summary (`Berita Acara UAT`) Block
```json
{
  "release_candidate": "v1.4.0-rc2",
  "environment": "staging-uat",
  "p0_p1_total": 42,
  "passed": 41,
  "failed": 0,
  "not_tested": 1,
  "open_defects": { "blocker": 0, "critical": 0, "major": 0, "minor": 2 },
  "gate_decision": "CONDITIONAL_SIGN_OFF_PENDING_HSM_PILOT",
  "evidence_bundle_sha256": "<sha256-of-uat-evidence-archive>"
}
```

## 4. Best Practices
- Seed Staging strictly with realistic **anonymized/synthetic fixtures** mimicking production volume and Indonesian edge formats (`NIK`, NPWP, Unicode names, timezones) — never dump unmasked production PII to Staging.
- Run explicit `E03` query-param difference checks (`count(unfiltered) !== count(filtered)`) so UI filters don't silently return unfiltered pages.

## 5. Anti-Patterns (`WRONG` vs `RIGHT`)
- **WRONG (Score-masking blockers & optimistic `NOT TESTED` reporting):** Recommending "Go Live (98% pass)" when 1 Critical cross-tenant IDOR or double-billing bug remains open, or marking an unexecuted check `PASS`.
  **RIGHT:** Block release immediately on any `Blocker`/`Critical` defect regardless of percentage, and explicitly record skipped flows as `NOT TESTED`.
- **WRONG (Happy-path-only UAT):** Clicking "Submit -> 200 OK" without testing invalid fields, duplicate clicks, expired tokens, or query filters.
  **RIGHT:** Pair every happy-path RTM row with negative/boundary assertions and visual mobile viewport evidence.

## 6. Production Considerations
- **Exit Gate to Release (`/shadow-release`) & Handover (`/shadow-handover`):** Preserve immutable UAT evidence bundles alongside signed Berita Acara UAT records so post-launch changes remain cleanly distinguished from signed baseline behavior (`/shadow-pmo`).
