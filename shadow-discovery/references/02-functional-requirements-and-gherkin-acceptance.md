# 02. Functional Requirements, Invariants & Executable Gherkin Acceptance Criteria

## 1. Purpose & Activation Conditions
Use this playbook when authoring Functional Requirements (`FR-*`), business state transitions, validation contracts, and deterministic `Given/When/Then` acceptance criteria inside a PRD, BRD, or SRS. Its goal is to eliminate untestable prose by making every P0 and P1 requirement directly executable as automated tests (`/shadow-test`) and Staging UAT scenarios (`/shadow-uat`).

Activate this playbook when:
- Translating validated discovery goals into concrete `FR-*` specifications.
- Modeling multi-step workflows (approvals, cancellations, refunds, settlements, SLA timers, role-gated actions).
- Red-teaming an existing draft PRD/SRS to expose missing negative paths, boundary inputs, concurrency races, or role bypasses.

## 2. Prerequisites
- Completed Stakeholder & Actor Matrix and resolved blocking ambiguities from [`01-epistemic-discovery-and-ambiguity-gates.md`](01-epistemic-discovery-and-ambiguity-gates.md).
- Explicit In-Scope (MVP) vs Out-of-Scope boundary.
- Knowledge of existing domain invariants and API conventions if operating in a brownfield codebase.

## 3. Technical Principles & Constraints
1. **Atomic, Singular Requirements**: Each `FR-MOD-NNN` describes one cohesive capability with one clear priority (`P0 | P1 | P2`), owning actor(s), state preconditions, invariants, and measurable outcomes. Never bundle unrelated features into one mega-paragraph.
2. **4-Path Completeness for Every P0/P1 Requirement**: Every P0/P1 `FR-*` MUST specify acceptance criteria covering all four paths:
   - **Happy Path**: Valid authorized actor, valid payload, exact persisted state + response contract.
   - **Negative Validation Path**: Boundary violations (`<= 0`, empty string, invalid timezone/currency, schema violation) returning `400`/`422` with zero partial state mutation.
   - **Role / Tenant Boundary Path**: Unauthenticated (`401`), unauthorized role or maker-checker self-approval (`403`), and cross-tenant isolation (`403`/`404` without metadata leak).
   - **Idempotency & Concurrency Path**: Duplicate submission (double-click/webhook retry) and stale optimistic-lock version (`409 Conflict`).
3. **Observable Outcomes Over Implementation Coupling**: Acceptance criteria assert external observable behavior (HTTP status, domain state, emitted event, visible UI state, audit record) rather than brittle internal helper names.
4. **Explicit State Machine Table**: Any stateful entity (`Order`, `Invoice`, `Ticket`, `Payout`) MUST declare an explicit allowed-transitions table including terminal states and forbidden transitions (`CANCELLED -> APPROVED` MUST fail closed).
5. **Traceable Stable Identifiers**: Link `FR-MOD-NNN -> AC-MOD-NNN-01` cleanly so `/shadow-plan` User Stories, `/shadow-test` test IDs, and `/shadow-uat` RTM rows preserve 1-to-1 traceability.

## 4. Architecture & Implementation
### Structured Functional Requirement & Gherkin Contract
```gherkin
Feature: FR-PO-012 Purchase Order Approval & Maker-Checker Enforcement
  As a Finance Approver
  I want to approve or reject submitted purchase orders within my cost-center limit
  So that expenditure stays compliant with dual-control policy

  Background:
    Given tenant "T-01" has requester "u-req-1" and approver "u-app-2" (limit IDR 50000000)
    And Purchase Order "PO-900" belongs to tenant "T-01" with amount IDR 12500000, version 3, state "PENDING_APPROVAL"

  @AC-PO-012-01 @happy-path
  Scenario: Authorized approver approves within limit
    When "u-app-2" sends POST /api/v1/purchase-orders/PO-900/approve with header "If-Match: W/\"3\"" and "Idempotency-Key: idem-po-900-a"
    Then the HTTP status is 200
    And Purchase Order "PO-900" transitions to state "APPROVED" at version 4
    And an immutable audit record is persisted with actor "u-app-2" and action "PO_APPROVED"

  @AC-PO-012-02 @negative-authz @maker-checker
  Scenario: Requester cannot self-approve own Purchase Order
    When "u-req-1" sends POST /api/v1/purchase-orders/PO-900/approve with header "If-Match: W/\"3\""
    Then the HTTP status is 403
    And error code is "MAKER_CHECKER_VIOLATION"
    And Purchase Order "PO-900" remains in state "PENDING_APPROVAL" at version 3

  @AC-PO-012-03 @negative-validation
  Scenario: Rejection requires a non-empty business reason
    When "u-app-2" sends POST /api/v1/purchase-orders/PO-900/reject with body {"reason": "   "}
    Then the HTTP status is 422
    And error field "reason" indicates minimum length 10 characters
    And Purchase Order "PO-900" remains in state "PENDING_APPROVAL"

  @AC-PO-012-04 @concurrency-conflict
  Scenario: Stale version approval fails closed without overwrite
    Given "PO-900" was already updated to version 4
    When "u-app-2" sends POST /api/v1/purchase-orders/PO-900/approve with header "If-Match: W/\"3\""
    Then the HTTP status is 409
    And error code is "VERSION_CONFLICT"
```

### Typed Traceability Contract for FR & Acceptance Criteria
```typescript
export type RequirementPriority = 'P0' | 'P1' | 'P2';
export type ScenarioCategory =
  | 'HAPPY_PATH'
  | 'NEGATIVE_VALIDATION'
  | 'ROLE_TENANT_BOUNDARY'
  | 'IDEMPOTENCY_CONCURRENCY';

export interface AcceptanceScenario {
  readonly acId: string;
  readonly category: ScenarioCategory;
  readonly given: readonly string[];
  readonly when: string;
  readonly then: readonly string[];
}

export interface FunctionalRequirementSpec {
  readonly frId: string;
  readonly title: string;
  readonly priority: RequirementPriority;
  readonly actors: readonly string[];
  readonly invariants: readonly string[];
  readonly scenarios: readonly AcceptanceScenario[];
}

const REQUIRED_P0_CATEGORIES: readonly ScenarioCategory[] = [
  'HAPPY_PATH',
  'NEGATIVE_VALIDATION',
  'ROLE_TENANT_BOUNDARY',
  'IDEMPOTENCY_CONCURRENCY',
] as const;

export function findMissingAcceptanceCategories(
  spec: FunctionalRequirementSpec,
): readonly ScenarioCategory[] {
  if (spec.priority === 'P2') {
    return [];
  }
  const present = new Set(spec.scenarios.map((scenario) => scenario.category));
  return REQUIRED_P0_CATEGORIES.filter((cat) => !present.has(cat));
}
```

## 5. Platform / Vendor Variations
- **REST / API-First Platforms**: Anchor `When` clauses to exact method, resource path, headers (`Idempotency-Key`, `If-Match`), and RFC 9457 error `code` so `/shadow-api` OpenAPI contracts match `1:1`.
- **Event-Driven & Async Workflows**: Explicitly split synchronous submission acceptance (`HTTP 202 Accepted` + `job_id`) from asynchronous terminal state (`COMPLETED | FAILED`), aligning with `shadow-design` Chapter 8 (`HTTP 202 != Done`).
- **Batch & Scheduled Back-Office Jobs**: Define acceptance criteria in terms of input batch fixture, cutoff timezone (`Asia/Jakarta`), deterministic reconciliation totals, partial-failure quarantine counts, and re-run idempotency.

## 6. Decision Matrix & Trade-Offs
| Specification Format | Best Fit | Limitation | Recommendation |
| :--- | :--- | :--- | :--- |
| **Gherkin (`Given/When/Then`)** | P0/P1 workflows, approvals, state transitions, auth & error boundaries | Verbose for large multi-column validation matrices | Mandatory for all P0/P1 behavioral requirements |
| **Decision Table (Condition -> Action)** | Complex pricing tiers, tax rules, multi-role RBAC matrices | Does not express temporal ordering alone | Pair with Gherkin scenarios for boundary rows |
| **State Transition Matrix** | Stateful aggregates (`DRAFT -> SUBMITTED -> APPROVED`) | Needs companion field-validation spec | Mandatory whenever entity has `>= 3` lifecycle states |
| **Free-form Narrative Prose** | Executive context & business background only | Untestable; invites contradictory interpretations | Never use as sole acceptance criterion for engineering |

## 7. Real Production Scenario
**Context:** An enterprise expense-reimbursement portal launched with a PRD stating only *"Managers can approve employee claims and finance disburses funds."*
**Failure:** During Staging UAT, QA discovered three production-blocking defects: (1) managers could approve their own claims when holding dual roles, (2) clicking Approve twice under slow mobile networks queued two duplicate disbursements, and (3) rejecting a claim cleared the employee's uploaded receipts permanently.
**Fix:** Rewriting `FR-EXP-004` with the 4-Path Gherkin standard surfaced the maker-checker invariant (`403`), `Idempotency-Key` deduplication (`200` replay with single payout), and `REJECTED -> DRAFT` receipt preservation rule before Sprint 2 coding started, cutting UAT rework defects by over half.

## 8. Failure Modes & Edge Cases
- **WRONG (Happy-path-only prose requirements):** Writing *"The user can filter orders by status and date and export them"* without defining filter parameters, invalid date ranges (`from > to`), empty-result behavior, timezone boundaries, or max export rows.
  **RIGHT:** Specify query parameters (`?status=&from=&to=`), timezone (`Asia/Jakarta`), invalid-range `422` response, `0`-row empty-state behavior, and async export threshold (`> 5,000` rows -> `HTTP 202`).
- **WRONG (Silent permission conflicts across modules):** Allowing `Role: Branch Manager` to delete customer records in `FR-CRM-009` while `FR-AUDIT-002` prohibits hard deletes of customers with historical invoices.
  **RIGHT:** Run a cross-FR Red-Team PRD check before Stage 1 exit; resolve the conflict explicitly (e.g., archive/deactivate with soft-delete tombstone, rejecting hard delete with `409 HAS_LINKED_INVOICES`).

## 9. Testing & Verification
- **4-Path Completeness Audit**: Verify every `P0` and `P1` `FR-*` has zero missing categories in `findMissingAcceptanceCategories` (Happy, Negative Validation, Role/Tenant Boundary, Idempotency/Concurrency).
- **Red-Team PRD Checklist**: Inspect every state transition table for orphan states (reachable but no exit except intentional terminal states) and illegal backward jumps.
- **Downstream Handoff Check**: Confirm every `FR-ID` and `AC-ID` maps directly into `/shadow-plan` vertical stories and `/shadow-uat` RTM rows without rewording business invariants.

## 10. Operational Considerations
- When a live production hotfix or approved Change Request modifies business rules, update the corresponding `FR-*` and `AC-*` first (via `/shadow-doc` selective block update) so specs never drift permanently behind production behavior.
- Keep example identifiers realistic and locale-accurate (`IDR` integer minor units or `NUMERIC(18,2)`, ISO-8601 timestamps with explicit offset `+07:00`, realistic Indonesian `NIK`/`NPWP` synthetic formats) — never embed real customer PII in specs.

## 11. Authoritative References
- **ISO/IEC/IEEE 29148:2018** — *Requirements characteristics (necessary, implementation-free, unambiguous, consistent, complete, singular, feasible, traceable, verifiable)*.
- **Cucumber / Gherkin Reference** — *Structured Behavior-Driven Specification (`Feature`, `Background`, `Scenario`, `Given/When/Then`)*.
- **Shadow Design PM Execution Pack** — `pm-execution/skills/create-prd/SKILL.md` & `pm-execution/commands/red-team-prd.md`.

## 12. Limitations & When NOT to Use
- **Do NOT use** for detailed aggregate internal implementation or database locking mechanics — hand complex domain invariants to `/shadow-domain` and physical schemas to `/shadow-db`.
- **Do NOT use** for visual component layout specs or token design — hand UI states and wireframes to `/shadow-design`.
- **Do NOT use** for contractual scope dispute arbitration — hand to `/shadow-pmo`.
