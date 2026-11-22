# 02. Aggregates, Invariants & Optimistic Locking

## 1. Purpose & Activation Conditions
Design tight Aggregate consistency boundaries that enforce multi-field business invariants, multi-tenant ownership, monetary precision, and optimistic-lock Compare-And-Swap (`version`) across domain logic and persistence. Load when building stateful entities with concurrent edits, approvals, quotas, or financial totals.

## 2. Prerequisites
- Bounded Context scope (`01-ddd-applicability-and-bounded-contexts.md`) and ACID transaction guarantees (`shadow-data` Module `04`).

## 3. Technical Principles & Constraints
- **Keep Aggregates Small (True Invariant Boundary Only):** Put two entities inside the same Aggregate ONLY when they MUST be consistent **immediately within the same ACID transaction** (e.g., `Order` + `OrderLines` enforcing `totalMinor === SUM(line.qty * line.unitPriceMinor)`). Reference other Aggregates strictly by **ID** (never load an entire `Tenant -> 50,000 Orders` object graph into memory!).
- **Single-Gatekeeper Encapsulation:** Never let HTTP controllers mutate entity fields directly (`order.status = 'APPROVED'`). Expose intention-revealing pure domain methods/functions (`approvePurchaseOrder`, `reassignDriver`, `reserveQuota`) returning **discriminated typed results** (`{ ok: true, next }` | `{ ok: false, code }`) so illegal states are structurally unrepresentable!
- **Optimistic Concurrency (`version` CAS) on Every Aggregate Root:** Carry a monotonic `version: number` on every aggregate root. Domain transitions check `order.version === expectedVersion`, increment `version + 1`, and persistence enforces `UPDATE ... SET version = version + 1 WHERE id = $1 AND tenant_id = $2 AND version = $3` — mapping `0` rows affected deterministically to HTTP **`409 Conflict`**!
- **Multi-Tenant & Monetary Invariants Everywhere:** Every aggregate carries immutable `tenantId`, stores money in integer minor units (`amountMinor`, never float), and enforces identical invariants across API DTOs, domain logic, and DB `CHECK` constraints!

## 4. Architecture & Implementation
```typescript
export interface OrderLine {
  readonly skuId: string;
  readonly quantity: number;
  readonly unitPriceMinor: number;
}

export interface PurchaseOrderAggregate {
  readonly id: string;
  readonly tenantId: string;
  readonly requesterId: string;
  readonly status: 'DRAFT' | 'PENDING_APPROVAL' | 'APPROVED' | 'REJECTED' | 'CANCELLED';
  readonly lines: readonly OrderLine[];
  readonly totalMinor: number;
  readonly version: number;
}

export type DomainMutationOutcome<T, E extends string> =
  | { readonly ok: true; readonly aggregate: T }
  | { readonly ok: false; readonly code: E };

export function addOrderLine(
  order: PurchaseOrderAggregate,
  actorTenantId: string,
  line: OrderLine,
  expectedVersion: number
): DomainMutationOutcome<
  PurchaseOrderAggregate,
  'TENANT_MISMATCH' | 'VERSION_CONFLICT' | 'NOT_EDITABLE' | 'INVALID_LINE'
> {
  if (order.tenantId !== actorTenantId) return { ok: false, code: 'TENANT_MISMATCH' };
  if (order.version !== expectedVersion) return { ok: false, code: 'VERSION_CONFLICT' };
  if (order.status !== 'DRAFT') return { ok: false, code: 'NOT_EDITABLE' };
  if (!Number.isInteger(line.quantity) || line.quantity <= 0 || !Number.isInteger(line.unitPriceMinor) || line.unitPriceMinor < 0) {
    return { ok: false, code: 'INVALID_LINE' };
  }
  const nextLines = [...order.lines, line];
  const nextTotalMinor = nextLines.reduce((sum, item) => sum + item.quantity * item.unitPriceMinor, 0);
  return {
    ok: true,
    aggregate: {
      ...order,
      lines: nextLines,
      totalMinor: nextTotalMinor,
      version: order.version + 1,
    },
  };
}
```
Persistence CAS update enforcing both tenant boundary and optimistic lock:
```sql
UPDATE purchase_orders
SET status = $1, total_minor = $2, version = version + 1, updated_at = NOW()
WHERE id = $3 AND tenant_id = $4 AND version = $5
RETURNING version;
```

## 5. Platform / Vendor Variations
| Contention Profile | Locking Strategy on Aggregate | Trade-Off |
| :--- | :--- | :--- |
| **Low–Medium Contention (Orders, Approvals, Profiles)** | **Optimistic CAS (`WHERE version = $expected`)** | Zero row-lock waits; returns `409 Conflict` cleanly on concurrent edit |
| **High Contention (Flash-Sale Stock / Hot Wallet)** | **Pessimistic `FOR UPDATE` or Atomic Conditional `UPDATE`** (`shadow-data`) | Avoids repeated optimistic retry storms |

## 6. Decision Matrix & Trade-Offs
| Aggregate Boundary Choice | Consistency | Lock Contention | Recommendation |
| :--- | :---: | :---: | :--- |
| **Small Focused Aggregate (`Order + Lines`)** | Strong inside tx | Low | **Default standard** |
| **God Aggregate (`Tenant + All Users + All Invoices`)** | Strong | Catastrophic (serializes whole tenant!) | **NEVER build God Aggregates** |
| **Cross-Aggregate Coordination (`Order -> Inventory`)** | Eventual via Outbox/Saga | Low | Reference by ID + Transactional Outbox (`shadow-concurrency`) |

## 7. Real Production Scenario
Two finance approvers open the same `PENDING_APPROVAL` purchase order simultaneously: Approver 1 clicks `"Approve"` while Approver 2 edits a line item total from `Rp 5M` to `Rp 50M`. Without `version` CAS and state invariants, Approver 2 overwrites the amount AFTER approval, authorizing a `Rp 50M` payout that was only approved for `Rp 5M`! Enforcing `status === 'DRAFT'` on line edits + `WHERE id = $1 AND tenant_id = $2 AND version = $3` guarantees the concurrent edit fails cleanly with `409 Conflict`.

## 8. Failure Modes & Edge Cases
- **WRONG:** Accepting client-calculated `totalMinor` in the API body and persisting it without recomputing `SUM(qty * unitPriceMinor)` inside the aggregate.
- **RIGHT:** Derive aggregate totals purely inside domain functions from validated line items (never trust client-computed totals!).
- **WRONG:** Mutating two separate aggregates (`Order` + `CustomerLoyaltyPoints`) inside one giant cross-service lock when eventual consistency via Outbox suffices.
- **RIGHT:** Commit the primary aggregate + `outbox_events` row atomically, and update secondary aggregates asynchronously via idempotent consumers.

## 9. Testing & Verification
- Write property/unit tests asserting every mutation preserves `totalMinor === SUM(line.qty * line.unitPriceMinor)`, rejects stale `expectedVersion`, rejects cross-tenant `actorTenantId`, and rejects negative quantities/prices.

## 10. Operational Considerations
- Expose `version` via HTTP `ETag` / `If-Match` headers (`shadow-api` Module `04`) so browser/mobile clients detect concurrent edits gracefully without silent overwrites.

## 11. Authoritative References
- Vaughn Vernon — *Effective Aggregate Design (Parts I–III)* (`https://www.dddcommunity.org/library/vernon_2011/`).
- Eric Evans — *Domain-Driven Design Reference* (Aggregates & Invariants).

## 12. Limitations & When NOT to Use
- Pure domain functions assume single-record snapshot consistency — always pair domain `version` checks with actual DB `WHERE version = $expected` persistence enforcement (`shadow-data`).
