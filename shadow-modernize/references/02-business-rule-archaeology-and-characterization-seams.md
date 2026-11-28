# 02. Business-Rule Archaeology, Seam Discovery & Characterization Harnesses

## 1. Purpose & Activation Conditions
Use this playbook BEFORE cutting a single migration slice out of a legacy monolith to excavate **hidden business rules** buried inside database triggers, stored procedures, cron batches, rounding quirks, and historical bug-fix workarounds, and lock their observable behavior behind **characterization tests** and clean **Anti-Corruption Seams**.

Activate this playbook when:
- Preparing to modernize an undocumented legacy core (`has_automated_tests == false`) where stakeholders say *"Nobody remembers all the rules, just read the code."*
- Auditing PostgreSQL/MySQL/Oracle/SQL Server triggers, views, stored procedures, and nightly batch scripts to build a Migration Dependency Map.
- Defining exact seams and Golden-Master characterization harnesses handed off to `/shadow-refactor` for safe slice extraction.

## 2. Prerequisites
- Completed read-only forensics and multi-dimensional risk vector from [`01-readonly-forensics-and-multidimensional-risk-vectors.md`](01-readonly-forensics-and-multidimensional-risk-vectors.md).
- Read-only schema dump (`pg_dump --schema-only` / `mysqldump --no-data --routines --triggers`) and anonymized synthetic test inputs (NEVER raw unmasked production PII!).

## 3. Technical Principles & Constraints
1. **The Legacy System IS the Specification**:
   - Written SRS documents for 5–15 year old systems are almost always stale. True business invariants hide in 5 archaeological strata:
     1. **Database Layer**: `TRIGGER`s, `STORED PROCEDURE`s, `CHECK`/`UNIQUE` constraints, materialized views, and implicit default values.
     2. **Application Layer**: Magic constants, date-threshold `if (created_at < '2021-07-01')` grandfather clauses, currency rounding (`HALF_UP` vs `FLOOR`), and status-code switchboards.
     3. **Scheduled / Cron Layer**: Nightly reconciliation scripts, OS `crontab`, Windows Task Scheduler jobs, and external Pentaho/SQL ETL pipes.
     4. **Integration & File-Drop Layer**: SFTP CSV feeds, bank ISO/MT940 parsers, legacy SOAP/XML headers, and external systems directly reading your DB views!
     5. **Operational Workarounds**: Support team runbooks and manual SQL patch scripts fixing recurring edge cases.
2. **Characterization Tests Before Any Cut**:
   - A characterization test records **what the legacy system actually outputs today** (even quirky edge cases!) across representative inputs so you distinguish intentional rule changes from accidental migration bugs.
   - Coordinate execution-level characterization test authoring cleanly with `/shadow-refactor` and `/shadow-test`.
3. **Database-Sharing Detection (Hidden Coupling Trap)**:
   - Before retiring or splitting any legacy table, check whether external BI tools, reporting scripts, or sibling applications connect directly to that database schema! Breaking a hidden direct-SQL consumer causes immediate silent downstream outages.
4. **Explicit Rule Disposition Classification**:
   - Classify every excavated rule with business-owner sign-off: `PRESERVE_EXACT` (statutory/financial invariant), `MODERNIZE_WITH_APPROVAL` (intentional policy update documented in `/shadow-discovery`), or `RETIRE_DEAD_RULE` (obsolete legacy promo/tax rule proven unreachable).

## 4. Architecture & Implementation
### Business-Rule Archaeology Ledger Template
| Rule ID | Archaeological Stratum | Location / Artifact | Observed Invariant | Business Disposition | Parity Test ID |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `ARCH-001` | DB Trigger | `sql/triggers/trg_invoice_tax.sql:42` | Invoices issued before `2022-04-01` keep `PPN 10%`; newer use `11%` | `PRESERVE_EXACT` | `CHAR-TAX-01` |
| `ARCH-002` | Nightly Cron | `/etc/cron.d/late_fee_calc` | Grace period skips Indonesian national holidays via static CSV | `MODERNIZE_WITH_APPROVAL` | `CHAR-FEE-02` |
| `ARCH-003` | External DB View | `vw_erp_gl_export` | ERP accounting tool reads view directly at `02:00 WIB` | `PRESERVE_EXACT` (keep facade view!) | `CHAR-GL-03` |

### Strict TypeScript Golden-Master Parity Comparator
```typescript
export interface ParityComparisonInput {
  readonly ruleId: string;
  readonly sampleKey: string;
  readonly legacyOutputJson: string;
  readonly candidateOutputJson: string;
  readonly allowedIgnoredFields: readonly string[];
}

export interface ParityMismatch {
  readonly ruleId: string;
  readonly sampleKey: string;
  readonly fieldPath: string;
  readonly legacyValue: unknown;
  readonly candidateValue: unknown;
}

export function compareLegacyAndCandidateOutputs(
  legacyRecord: Readonly<Record<string, unknown>>,
  candidateRecord: Readonly<Record<string, unknown>>,
  ruleId: string,
  sampleKey: string,
  ignoredFields: ReadonlySet<string>,
): readonly ParityMismatch[] {
  const mismatches: ParityMismatch[] = [];
  const allKeys = new Set([
    ...Object.keys(legacyRecord),
    ...Object.keys(candidateRecord),
  ]);
  for (const key of allKeys) {
    if (ignoredFields.has(key)) {
      continue;
    }
    const left = JSON.stringify(legacyRecord[key]);
    const right = JSON.stringify(candidateRecord[key]);
    if (left !== right) {
      mismatches.push({
        ruleId,
        sampleKey,
        fieldPath: key,
        legacyValue: legacyRecord[key],
        candidateValue: candidateRecord[key],
      });
    }
  }
  return mismatches;
}
```

## 5. Platform / Vendor Variations
- **Oracle / SQL Server / PostgreSQL Trigger-Heavy Cores**: Inspect `information_schema.triggers`, `pg_proc`, and DB user roles (`pg_roles`) to list EVERY external credential querying tables or views before designing Strangler API boundaries.
- **Legacy PHP / CodeIgniter / Laravel / Java EE**: Map global middleware, session cookies, and implicit autoload helpers before placing an Nginx/API Gateway reverse proxy in front to route migrated URL paths incrementally.

## 6. Decision Matrix & Trade-Offs
| Hidden Coupling Found | Extraction Pattern | Trade-Off |
| :--- | :--- | :--- |
| **External system reads legacy SQL view directly** | Maintain backward-compatible SQL view / CDC sync during transition (`Expand-Contract` `/shadow-data`) | Temporary dual maintenance; prevents silent ERP/BI breakage |
| **Complex financial calc locked in legacy stored proc** | Build Golden-Master characterization suite -> port calculation -> shadow-compare 100% of synthetic & replay inputs | Extra parity test phase; eliminates Rupiah/rounding bugs |
| **Shared auth cookie across legacy + new slice** | Bridge via shared SSO/OIDC token gateway (`/shadow-auth` — preserving `your-org-sso` if present) | Seamless UX across strangled routes |

## 7. Real Production Scenario
**Context:** A government licensing platform began rewriting its fee calculator in TypeScript based on a 2019 Word manual. During archaeology, the team inspected `pg_dump --schema-only` and discovered two PostgreSQL triggers applying grandfather fee waivers for pre-2021 permits plus a read-only SQL view consumed nightly by the finance ministry's reporting bridge.
**Impact:** Documenting `ARCH-001` and `ARCH-003` and preserving the read-only SQL view facade during Strangler cutover prevented both incorrect retroactive citizen billing and an automated finance-reconciliation failure on launch night.

## 8. Failure Modes & Edge Cases
- **WRONG (Trusting a 4-year-old PRD/Word manual as complete truth without reading DB triggers, cron jobs, or external DB readers):** Migrates only 70% of real rules and breaks hidden finance/ERP integrations on cutover day.
  **RIGHT:** Excavate all 5 archaeological strata (DB, App, Cron, Integrations/Views, Support Runbooks) and lock behavior with characterization tests before cutting any slice.
- **WRONG (Silently changing rounding or grandfather-clause behavior without business approval):** Causes subtle 1-Rupiah accounting ledger imbalances across thousands of historical invoices.
  **RIGHT:** Tag every discovered quirk `PRESERVE_EXACT` unless business stakeholders formally sign off `MODERNIZE_WITH_APPROVAL`.

## 9. Testing & Verification
- Verify `100%` of `PRESERVE_EXACT` archaeological rules have at least one automated characterization or Golden-Master parity test (`0` unexplained mismatches across synthetic edge cases).
- Confirm all external DB roles/views are cataloged in the Migration Dependency Map before scheduling table deprecation.

## 10. Operational Considerations
- Pair archaeology sessions with senior operations/support staff (often the only people who know the recurring month-end manual SQL workarounds!) and record their tribal knowledge in structured artifacts before key staff rotate off.

## 11. Authoritative References
- **Michael Feathers (2004)** — *Working Effectively with Legacy Code* (Characterization Testing & Pinch Points).
- **Sam Newman (2019)** — *Monolith to Microservices* (Database Decomposition, Strangler Fig & Parallel Run).
- **Shadow Modernize Playbooks** — [`../playbooks/DUE-DILIGENCE-AND-CUTOVER-TEMPLATES.md`](../playbooks/DUE-DILIGENCE-AND-CUTOVER-TEMPLATES.md).

## 12. Limitations & When NOT to Use
- **Do NOT use** live unmasked production PII tables to feed local characterization tests — anonymize or synthesize fixtures first (`/shadow-privacy`).
- **Do NOT execute** code-level refactoring commits directly inside `/shadow-modernize` due diligence — hand approved slices to `/shadow-refactor`.
