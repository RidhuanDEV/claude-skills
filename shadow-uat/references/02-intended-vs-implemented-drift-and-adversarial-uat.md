# 02. Intended-vs-Implemented Drift, `E03` Filter Audits & Adversarial UAT

## 1. Purpose & Activation Conditions
Use this playbook BEFORE inviting client testers into Staging to run an internal **Intended-vs-Implemented Drift Audit**, **`E03` Query/Filter Contract Audit**, and **12-Domain Adversarial UAT Walkthrough**. Its goal is to catch silent UI/API contract drift, ignored search/filter parameters, premature `HTTP 202` completion toasts, and state-machine omissions before stakeholders lose trust during live UAT sessions.

Activate this playbook when:
- Preparing a Staging build for internal QA sign-off ahead of client UAT.
- Auditing list/search/report screens to verify query parameters genuinely filter server responses (`E03` contract check).
- Verifying async workflows (`HTTP 202`), multi-tab concurrent edits (`409`/`ETag`), double-click submissions, and privacy-safe telemetry.

## 2. Prerequisites
- Signed `FEATURE-DESIGN.md` / PRD acceptance criteria (`/shadow-design`, `/shadow-discovery`) representing the **Intended** baseline.
- Running Staging environment (or verified local build) exposing the **Implemented** UI, API endpoints, and background workers.
- Browser verification capabilities (`/shadow-browser`) for responsive `375px`/`1440px` + `200%` zoom checks when UI changed.

## 3. Technical Principles & Constraints
1. **Intended-vs-Implemented Reconciliation**: Diff every agreed requirement, applicable 9-state UI behavior, role boundary, and async status against actual observed Staging behavior — never rely on commit messages or PR descriptions as proof of implementation.
2. **`E03` Query & Filter Contract Verification**: Every filtered list or export endpoint MUST be probed to prove that passing `?status=PAID&from=2026-01-01&to=2026-01-31&q=inv` genuinely changes the returned result set (`filteredIds != unfilteredIds` when mixed data exists) and never silently drops unknown or misnamed query parameters (e.g., frontend sending `dateFrom` while backend reads `from_date`!).
3. **Async (`HTTP 202`) Honesty Check**: Whenever a mutation returns `HTTP 202 Accepted` (export, settlement, document indexing, AI batch), verify the UI displays `Submitted / Queued / Processing` progress and NEVER flashes a premature green `"Completed"` toast before worker confirmation arrives.
4. **Adversarial Resilience Probes**: Test double-clicking submit buttons, refreshing mid-request, submitting expired sessions (`401`), unauthorized tenant IDs (`403`/`404`), stale `ETag` updates (`409`), and invalid Unicode/boundary payloads (`422`) — confirming user input is preserved on validation errors and zero duplicate financial records are created.
5. **Privacy-Safe Outcome Telemetry Audit**: Inspect network/console logs during UAT flows to verify analytics/telemetry events fire without leaking raw `password`, `Authorization`, `NIK`, tokens, or PII into URL query strings or browser console errors.

## 4. Architecture & Implementation
### `E03` Query-Parameter Drift & Filter Contract Verifier (Strict TypeScript)
```typescript
export interface FilterProbeResult {
  readonly endpoint: string;
  readonly filterQuery: string;
  readonly unfilteredIds: readonly string[];
  readonly filteredIds: readonly string[];
  readonly expectedExcludedId: string;
}

export interface DriftFinding {
  readonly code: 'E03_SILENT_FILTER_IGNORED' | 'E03_EMPTY_BASELINE_FIXTURE';
  readonly endpoint: string;
  readonly detail: string;
}

export function detectFilterContractDrift(
  probe: FilterProbeResult,
): DriftFinding | null {
  if (probe.unfilteredIds.length < 2) {
    return {
      code: 'E03_EMPTY_BASELINE_FIXTURE',
      endpoint: probe.endpoint,
      detail: 'Staging fixture needs >= 2 contrasting records (matching + non-matching) to test filtering.',
    };
  }
  const excludedStillReturned = probe.filteredIds.includes(
    probe.expectedExcludedId,
  );
  if (excludedStillReturned) {
    return {
      code: 'E03_SILENT_FILTER_IGNORED',
      endpoint: probe.endpoint,
      detail: `Query '${probe.filterQuery}' still returned non-matching record '${probe.expectedExcludedId}' (possible param name drift).`,
    };
  }
  return null;
}
```

### Pre-Client Staging Drift Audit Checklist
| Audit Area | Concrete Staging Probe | Pass Condition |
| :--- | :--- | :--- |
| **9-State UI Parity** | Load empty tenant, apply zero-match filter, simulate `500`/`403` error | 3 distinct states shown; API error never disguised as `"0 records"` |
| **`E03` Filter/Sort/Page** | Compare `GET /orders` vs `GET /orders?status=PAID&sort=-createdAt` | Non-`PAID` IDs strictly excluded; sort order verified across page 1 & page 2 |
| **Double-Submit & Refresh** | Rapid double-click on Submit + hard refresh during in-flight POST | Submit button locks; `Idempotency-Key` prevents duplicate DB rows |
| **Concurrent Edit (`409`)** | Open same record in Tab A & Tab B; save Tab A, then save Tab B | Tab B receives `409 Conflict` with diff/reload recovery (zero silent overwrite) |
| **Responsive & Zoom** | Inspect primary flow at `375px` mobile, `1440px` desktop, and `200%` zoom | Zero horizontal overflow, visible focus rings, `44x44px` tap targets |
| **Async `HTTP 202`** | Trigger async bulk export / settlement job | Shows `Queued / Processing` badge; switches to `Completed` only after terminal status |

## 5. Platform / Vendor Variations
- **SPA + REST/GraphQL Apps**: Pay special attention to camelCase vs snake_case parameter drift (`startDate` vs `start_date`) and React Query/SWR stale cache masking fresh server rejections.
- **Multi-Tenant SaaS**: Include an explicit cross-tenant ID-tampering probe (`Tenant A` user requesting `Tenant B` record ID via URL or API) verifying fail-closed `403`/`404` with zero metadata disclosure.
- **Batch / Webhook-Driven Systems**: Probe duplicate webhook delivery and out-of-order status events (`COMPLETED` followed by delayed `PROCESSING`) to verify monotonic state protection.

## 6. Decision Matrix & Trade-Offs
| Drift Finding | Severity | Action Before Client UAT |
| :--- | :--- | :--- |
| **Ignored filter parameter returning cross-status/wrong-tenant data (`E03`)** | `Critical` / `Blocker` | Halt client UAT invite; fix parameter contract + add automated regression test |
| **Silent overwrite on concurrent edit (`409` missing on financial record)** | `Critical` | Fix optimistic locking (`If-Match` / version check) before sign-off |
| **Premature green `"Completed"` toast on `HTTP 202`** | `Critical` (UX honesty) | Replace with truthful queued status tracker before sign-off |
| **Minor spacing tweak on secondary empty illustration** | `Minor` | Log in Defect Register; does not block Staging UAT execution |

## 7. Real Production Scenario
**Context:** A B2B finance dashboard passed all unit tests and looked healthy in Staging. During the pre-client `E03` filter audit, QA selected `Status = APPROVED` and `Date = 2026-04-01..2026-04-07`, noticing the row count stayed `48` (identical to unfiltered).
**Root Cause:** The React frontend sent `?date_from=...&status_filter=APPROVED`, while the backend controller parsed `from` and `status` and silently ignored unrecognized query keys—causing the CSV export button to download **all** draft and rejected invoices across the entire year!
**Impact Prevented:** Catching `E03_SILENT_FILTER_IGNORED` before client UAT prevented an embarrassing demo failure and a financial reporting error on Go-Live.

## 8. Failure Modes & Edge Cases
- **WRONG (Testing filters on a Staging DB with only 1 status present):** Running `GET /orders?status=PAID` when every seeded order in Staging happens to be `PAID`, falsely concluding filtering works.
  **RIGHT:** Seed Staging with mixed contrasting records (`DRAFT`, `PENDING`, `PAID`, `CANCELLED` across multiple dates and tenants) and assert that non-matching IDs are strictly absent from filtered output.
- **WRONG (Only verifying HTTP `200 OK` on happy paths):** Ignoring double-clicks, stale tabs, expired sessions, and `375px` mobile reflow during UAT prep.
  **RIGHT:** Run the full adversarial probe table before declaring Staging ready for client testers.

## 9. Testing & Verification
- Run `python -m unittest discover -s shadow-uat/tests -v` (`test_batch_uat_and_param_drift.py` validates parameter-drift detection and batch UAT evidence rules).
- Cross-reference browser checks with `/shadow-browser` (Playwright console/pageerror zero-defect oracle + `375px`/`768px`/`1440px` overflow checks).

## 10. Operational Considerations
- Convert every drift bug caught during pre-client Staging UAT into a permanent automated regression test in `/shadow-test` so the same parameter mismatch or missing state can never regress in a future sprint.

## 11. Authoritative References
- **Shadow Design Upstream QA Packs** — `pm-ai-shipping/commands/ship-check.md`, `designer-skills/design-ops/skills/design-qa-checklist/SKILL.md`, `pm-execution/skills/test-scenarios/SKILL.md`, and `ghaida-intent/skills/measure/SKILL.md`.
- **Shadow Design State Machine Pack** — [`03-state-machine-and-edge-cases.md`](../../shadow-design/references/ai-product-designer-skill-pack/03-state-machine-and-edge-cases.md).

## 12. Limitations & When NOT to Use
- **Do NOT use** this playbook to perform deep server-side root-cause debugging of complex stack traces or memory leaks — hand verified UAT failures to `/shadow-debug`.
- **Do NOT use** for load/stress/soak testing — route explicitly approved staging load campaigns to `/shadow-perf`.
