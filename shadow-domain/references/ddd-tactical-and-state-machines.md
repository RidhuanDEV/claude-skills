# DDD Tactical Modeling, Explicit State Machines & Domain Invariants

> Use this playbook when modeling complex state transitions, approval/cancellation policies, monetary invariants, bounded contexts, or optimistic-lock aggregates — and knowing when to keep simple CRUD lightweight.

## 1. Core Concepts
Domain-Driven Design (DDD) protects **consistency boundaries** where broken state transitions corrupt money, compliance, or audit trails:
- **Aggregate Root:** The sole gatekeeper allowed to mutate child entities and enforce multi-field invariants atomically within one transaction.
- **Discriminated Domain Outcomes + Optimistic Versioning:** Illegal transitions or stale versions return explicit typed domain rejections (`409 Conflict` / `422 Unprocessable Entity`) instead of silently overwriting concurrent edits.

## 2. Technical Rules & Decision Matrix

| Domain Complexity | Model to Pick | Why / Invariant Guard |
| :--- | :--- | :--- |
| Lookup tables, simple settings, read-heavy CRUD | **Transaction Script / Thin Service** | Zero DDD ceremony overhead; direct schema validation + SQL |
| Stateless cross-entity rules / tax / fee math | **Pure Domain Service** | Deterministic pure functions; trivial property/unit tests |
| Money transfers, multi-step approvals, cancellations, quotas | **Aggregate Root + Finite State Machine** | Explicit `ALLOWED_TRANSITIONS` table + maker-checker + `version` CAS guard |
| Cross-context notifications (Order -> Billing/Email) | **Domain Event + Transactional Outbox** | Emitted in outbox table inside commit tx; never fired before DB commit |

## 3. Implementation Examples

### Strict-TS Explicit Finite State Machine + Maker-Checker + Version Guard
```ts
export type OrderStatus = "DRAFT" | "PENDING_APPROVAL" | "APPROVED" | "REJECTED" | "CANCELLED";

const ALLOWED_TRANSITIONS: Readonly<Record<OrderStatus, readonly OrderStatus[]>> = {
  DRAFT: ["PENDING_APPROVAL", "CANCELLED"],
  PENDING_APPROVAL: ["APPROVED", "REJECTED", "CANCELLED"],
  APPROVED: ["CANCELLED"], // Only via explicit compensated cancellation path
  REJECTED: [],
  CANCELLED: [],
};

export interface PurchaseOrder {
  readonly id: string;
  readonly requesterId: string;
  readonly status: OrderStatus;
  readonly amountMinor: number;
  readonly version: number;
}

export type TransitionResult =
  | { readonly ok: true; readonly next: PurchaseOrder }
  | { readonly ok: false; readonly code: "INVALID_STATE" | "MAKER_CHECKER_VIOLATION" | "VERSION_CONFLICT" | "INVALID_AMOUNT" };

export function approvePurchaseOrder(
  order: PurchaseOrder,
  approverId: string,
  expectedVersion: number,
): TransitionResult {
  if (order.version !== expectedVersion) return { ok: false, code: "VERSION_CONFLICT" };
  if (!ALLOWED_TRANSITIONS[order.status].includes("APPROVED")) return { ok: false, code: "INVALID_STATE" };
  if (approverId === order.requesterId) return { ok: false, code: "MAKER_CHECKER_VIOLATION" };
  if (order.amountMinor <= 0) return { ok: false, code: "INVALID_AMOUNT" };

  return {
    ok: true,
    next: { ...order, status: "APPROVED", version: order.version + 1 },
  };
}
```
```sql
-- Persistence layer enforces atomic Compare-And-Swap (CAS) on the DB row
UPDATE purchase_orders
SET status = $1, version = version + 1, updated_at = NOW()
WHERE id = $2 AND version = $3
RETURNING version;
```

## 4. Best Practices
- Represent currency strictly in integer minor units (`amountMinor` in Rupiah/cents) paired with ISO currency codes rather than IEEE-754 floating-point numbers.
- Separate **anti-corruption layers (ACL)** around external ERP/payment payloads so upstream vendor status names never leak into core domain state enums.
- Escalate ambiguous business policies (e.g., whether approving/cancelling an expired voucher refunds fee or charges penalty) directly to the Monarch rather than guessing silently.

## 5. Anti-Patterns (`WRONG` vs `RIGHT`)
- **WRONG (Controller mutating status directly without transition or version check):** Writing `await db.orders.update({ where: { id }, data: { status: req.body.status } })` (allows jumping `DRAFT -> CANCELLED` or self-approval and loses concurrent updates).
  **RIGHT:** Validate transitions through `ALLOWED_TRANSITIONS`, verify maker-checker & invariants in pure domain functions, and persist with `WHERE id = $1 AND version = $2`.
- **WRONG (Cargo-cult DDD on a 3-column tag/category CRUD table):** Creating Value Objects, Factories, Repositories, and Domain Events for static reference data.
  **RIGHT:** Keep simple CRUD thin; reserve full Aggregate + FSM modeling for stateful business invariants.

## 6. Production Considerations
- **Race Recovery:** Map zero rows affected on CAS `UPDATE ... WHERE version = $expected` deterministically to HTTP `409 Conflict` so clients fetch fresh state cleanly.
- **Static Verification:** Validate state models offline with `python shadow-domain/scripts/domain_invariant_verifier.py --verify-model path/to/domain_model.json` before coding.
