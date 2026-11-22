# 04. Domain Events, Anti-Corruption Layers & Invariant Testing

## 1. Purpose & Activation Conditions
Connect Bounded Contexts cleanly using **Domain Events vs Versioned Integration Events**, isolate dirty external ERP/vendor models behind **Anti-Corruption Layers (ACL)**, and prove business-rule correctness via property-based & state-matrix tests. Load when integrating legacy external systems into clean core domains or designing domain event contracts.

## 2. Prerequisites
- Defined Bounded Contexts (`01`), Aggregates (`02`), and FSM transitions (`03`), plus Transactional Outbox infrastructure (`/shadow-concurrency`).

## 3. Technical Principles & Constraints
- **Domain Events vs Integration Events (Do NOT Conflate!):**
  - **Internal Domain Events:** Fine-grained facts raised inside a Bounded Context (`PurchaseOrderApproved`, `DriverReassigned`). Can evolve freely within that module.
  - **Public Integration Events:** Explicitly versioned, minimal, backward-compatible contracts (`orders.approved.v1`) written to `outbox_events` inside the SAME ACID transaction as the aggregate save and published to other contexts/services! NEVER emit raw ORM entities as integration events!
- **Emit Events AFTER Commit (Via Transactional Outbox):** NEVER dispatch an in-memory/queue event *before* the DB transaction commits — if commit rolls back, downstream billing/email receives a phantom event for a non-existent order!
- **Anti-Corruption Layer (ACL) Around Legacy/External Systems:** When integrating legacy ERPs, payment gateways (`Midtrans`, `SNAP BI`), or government APIs (`SatuSehat`, `Dukcapil`), translate every external payload through an explicit **ACL adapter** (`externalStatus -> DomainStatus`) at the boundary so cryptic codes (`"ST_99_X"`) and nullability quirks never infect core domain invariants!
- **Executable Invariant & Property-Based Testing:** Verify domain purity by testing invariants across randomized action sequences (`fast-check` / `Hypothesis`): e.g., across ANY random sequence of `submit`, `approve`, `reject`, `cancel`, `reassign`, the aggregate NEVER enters an illegal status, `totalMinor` ALWAYS equals line sum, and `version` strictly increases!

## 4. Architecture & Implementation
```typescript
// Anti-Corruption Layer translating external legacy ERP status codes cleanly into core Domain Status
export type CoreShipmentStatus = 'PREPARING' | 'IN_TRANSIT' | 'DELIVERED' | 'FAILED_RETURNED';

export interface ExternalErpShipmentPayload {
  readonly legacy_code: unknown;
  readonly ref_no: unknown;
  readonly updated_epoch_ms: unknown;
}

export type AclParseResult =
  | { readonly ok: true; readonly referenceNo: string; readonly status: CoreShipmentStatus; readonly occurredAtMs: number }
  | { readonly ok: false; readonly reason: 'INVALID_SHAPE' | 'UNKNOWN_EXTERNAL_STATUS' };

const ERP_STATUS_MAP: Readonly<Record<string, CoreShipmentStatus>> = {
  ERP_PACKING: 'PREPARING',
  ERP_ON_ROAD: 'IN_TRANSIT',
  ERP_POD_OK: 'DELIVERED',
  ERP_RTO_FAIL: 'FAILED_RETURNED',
};

export function translateExternalErpShipment(raw: ExternalErpShipmentPayload): AclParseResult {
  if (typeof raw.legacy_code !== 'string' || typeof raw.ref_no !== 'string' || typeof raw.updated_epoch_ms !== 'number') {
    return { ok: false, reason: 'INVALID_SHAPE' };
  }
  const mapped = ERP_STATUS_MAP[raw.legacy_code.trim().toUpperCase()];
  if (!mapped) {
    // Fail closed (route to DLQ / alert) instead of silently defaulting unknown vendor codes to DELIVERED!
    return { ok: false, reason: 'UNKNOWN_EXTERNAL_STATUS' };
  }
  return {
    ok: true,
    referenceNo: raw.ref_no.trim(),
    status: mapped,
    occurredAtMs: raw.updated_epoch_ms,
  };
}
```
Transactional Outbox event contract emitted alongside aggregate mutation:
```typescript
export interface IntegrationEventV1 {
  readonly eventType: 'orders.approved.v1';
  readonly eventId: string;
  readonly aggregateId: string;
  readonly tenantId: string;
  readonly aggregateVersion: number;
  readonly occurredAtIso: string;
  readonly payload: { readonly totalMinor: number; readonly currency: string; readonly approverId: string };
}
```

## 5. Platform / Vendor Variations
| Integration Boundary | ACL Defense Pattern | Failure Handling |
| :--- | :--- | :--- |
| **External Payment / ERP Webhook** | Strict allowlist status mapper + minor-unit normalization (`translateExternalErpShipment`) | Unknown vendor status -> quarantine to DLQ + alert (never silent default!) |
| **Cross-Context Internal Event** | Versioned `outbox_events` (`orders.approved.v1`) with `aggregateVersion` | Consumers guard idempotently with monotonic `aggregateVersion` |

## 6. Decision Matrix & Trade-Offs
| Testing Strategy | What Bugs It Catches | Effort |
| :--- | :--- | :---: |
| **Exhaustive FSM `N × N` Matrix Test** | Missing transition guard, terminal-state reopen | Low (Mandatory) |
| **Property-Based Stateful Model Test (`fast-check` / `Hypothesis`)** | Weird 5-step sequence (`draft -> submit -> cancel -> edit`) breaking totals/invariants | Medium (High ROI on money/scheduling) |
| **ACL Contract Fixture Test** | Vendor adding unexpected status code or `null` field | Low (Mandatory on all external adapters) |

## 7. Real Production Scenario
An external courier API introduces a new status `"ERP_CUSTOMS_HOLD"`. Because the backend had no ACL and used `status === 'ERP_POD_OK' ? 'DELIVERED' : 'IN_TRANSIT'`, customs-held packages stayed `"IN_TRANSIT"` silently — and a second fallback mistakenly treated unknown statuses as `"DELIVERED"`, releasing escrow payouts prematurely! Adding `translateExternalErpShipment` failing closed (`UNKNOWN_EXTERNAL_STATUS` -> DLQ + alert) stops premature payouts completely.

## 8. Failure Modes & Edge Cases
- **WRONG:** Publishing domain events via `eventEmitter.emit('order.approved')` BEFORE `await tx.commit()` succeeds.
- **RIGHT:** Persist `IntegrationEventV1` into `outbox_events` INSIDE the same DB transaction (`shadow-concurrency`).
- **WRONG:** Letting third-party ERP enum strings (`ERP_POD_OK`) leak directly into PostgreSQL columns, frontend components, and reporting queries.
- **RIGHT:** Translate strictly at the ACL boundary so external vendor renames only touch one small adapter file.

## 9. Testing & Verification
- Run `python shadow-domain/scripts/domain_invariant_verifier.py --self-test` and `python -m unittest discover -s shadow-domain/tests -v`.
- Add negative ACL tests feeding unknown vendor status strings, missing fields, and negative amounts -> assert clean `ok: false` fail-closed handling.

## 10. Operational Considerations
- Version every public integration event (`*.v1` -> `*.v2`) using additive evolution rules (`/shadow-compat`) so downstream subscribers never crash during rolling upgrades.

## 11. Authoritative References
- Eric Evans — *Domain-Driven Design* (Anti-Corruption Layer & Published Language).
- Chris Richardson — *Microservices Patterns: Transactional Outbox & Domain Events* (`https://microservices.io/patterns/data/transactional-outbox.html`).

## 12. Limitations & When NOT to Use
- Do NOT adopt full Event Sourcing (storing ONLY events and rebuilding state from event replay) unless audit replay/time-travel is a proven core domain requirement — state-based Aggregates + Outbox Integration Events + immutable `audit_logs` deliver 95% of the benefits with 10% of the operational complexity.
