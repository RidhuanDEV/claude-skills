# Safe Seam Extraction, Characterization Tests & Strangler Refactoring

> Use this playbook when refactoring legacy modules, extracting pure seams without altering external behavior, or preserving DB/event ordering guarantees.

## 1. Core Concepts
Refactoring means restructuring internal implementation **without altering observable behavior** (outputs, error codes, DB side-effect ordering, API contracts):
- **Characterization (Golden Master) First:** Never refactor untested legacy code blind. Pin existing inputs, edge cases (including existing quirks/rounding), and side-effect ordering with automated tests *before* moving code.
- **Smallest Reversible Step:** Isolate pure domain math from I/O (`Clock`, `Repository`, `Mailer`) via dependency seams rather than rewriting whole subsystems in one unreviewable diff.

## 2. Technical Rules & Decision Matrix

| Situation | Safe Technique | Verification Gate |
| :--- | :--- | :--- |
| Monolithic helper inside 1 well-scoped file | **Direct Pure Helper Extraction** | Unit tests pass before & after; diff strictly within file |
| Function tightly coupled to `Date.now()`, globals, or raw SDK | **Seam / Port Injection** (`Clock`, narrow interface) | Characterization test asserts exact output + call sequence |
| Swapping core algorithm live in high-risk hot path | **Branch-by-Abstraction** (parallel read/verify shadow) | Compare old vs new results on production-like fixtures before removing old path |
| Decoupling sprawling legacy route from DB/side effects | **Strangler Seam Adapter** (preserve route & SSO contracts) | Contract tests + `refactor_characterization_gate.py` |

## 3. Implementation Examples

### Characterization (Golden Master) Test Locking Quirks + Clean Seam Extraction
```ts
// 1. Write BEFORE refactoring: locks exact legacy behavior & side-effect sequence
import assert from "node:assert/strict";

export interface SideEffectLog {
  readonly events: string[];
}

// 2. Extracted pure pricing seam decoupled from Date.now() and repository I/O
export function computeLegacyDiscountCents(subtotalCents: number, tier: string, isPromoDay: boolean): number {
  if (subtotalCents < 0) throw new RangeError("INVALID_SUBTOTAL");
  const rate = tier === "VIP" ? 0.15 : isPromoDay ? 0.05 : 0;
  // Intentionally preserves Math.floor rounding semantics observed in legacy checkout
  return Math.floor(subtotalCents * rate);
}

// Characterization regression test (passes identically pre- and post-extraction)
export function runDiscountCharacterization(): void {
  assert.equal(computeLegacyDiscountCents(10_005, "VIP", false), 1_500);
  assert.equal(computeLegacyDiscountCents(10_005, "STANDARD", true), 500);
  assert.equal(computeLegacyDiscountCents(0, "VIP", true), 0);
}
```

### Preserving Exact `DB_COMMIT -> EVENT_PUBLISH` Ordering Across Seams
```ts
export interface OrderPorts {
  readonly saveAndCommit: (orderId: string) => Promise<void>;
  readonly enqueueWebhook: (orderId: string) => Promise<void>;
}

export async function completeOrderRefactorSafe(ports: OrderPorts, orderId: string): Promise<void> {
  // Preserve side-effect invariant: persistence commits BEFORE external notification
  await ports.saveAndCommit(orderId);
  await ports.enqueueWebhook(orderId);
}
```

## 4. Best Practices
- Remove dead code (unused helpers, stale interfaces, orphaned imports) **only within the refactored scope** once tests confirm zero callers remain.
- Preserve existing package managers, internal APIs, and local/SSO SDK boundaries (`file:../sdk/...`) rather than swapping dependencies opportunistically.
- Run `python shadow-refactor/scripts/refactor_characterization_gate.py --verify-plan path/to/plan.json` to ensure risk invariants and rollback steps are covered.

## 5. Anti-Patterns (`WRONG` vs `RIGHT`)
- **WRONG ("Drive-by" formatting + behavioral fix + rewrite in one diff):** Renaming public JSON fields, subtly changing rounding from `Math.floor` to `Math.round`, and reformatting unrelated directories without baseline tests.
  **RIGHT:** Commit characterization tests -> extract narrow seams with identical semantics -> fix genuine bugs in a **separate explicit commit/step** -> clean local dead code.
- **WRONG (Swapping `Promise.all([db.save(), mailer.send()])` for sequential steps):** Running side effects concurrently where persistence previously happened before notification (fires webhook on failed DB commit!).
  **RIGHT:** Record and assert exact side-effect ordering in tests before refactoring async flows.

## 6. Production Considerations
- **Approval Scope (`L1` vs `L2`):** Refactoring inside explicitly requested modules with local verification is `L1_SAFE_VERIFICATION`; expanding cleanup into unrelated modules requires `L2` Monarch approval.
- **Backward Compatibility:** Pair public API/schema cleanups with `/shadow-compat` Expand-Contract checks before removing any exported symbols.
