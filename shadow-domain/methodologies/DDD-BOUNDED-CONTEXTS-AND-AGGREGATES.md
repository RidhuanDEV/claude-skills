# Bounded Contexts, Aggregates & Business Invariant Methodology

## 1. DDD Applicability Threshold
- **Use DDD Aggregates & State Machines when:** Multiple fields must change atomically together (`balance + ledger_entry`), multi-actor approvals/cancellations race concurrently, or temporal/regulatory rules forbid invalid state sequences.
- **Avoid DDD Ceremony when:** Building simple reference tables, static CMS content, or single-row CRUD without stateful invariants.

## 2. Core Tactical Design Rules
1. **Aggregate Root Consistency Boundary:** Only one aggregate instance is modified per ACID transaction; cross-aggregate consistency uses domain/integration events + eventual consistency (`/shadow-concurrency`).
2. **Illegal State Unrepresentable:** Validate invariants inside aggregate command methods AND enforce matching DB constraints (`CHECK`, partial `UNIQUE`, `tenant_id` scoped FKs).
3. **Adversarial Edge Cases:**
   - **Concurrent Approvals:** Second approval against stale `version` must fail (`409 Conflict`).
   - **Cancellation After Completion:** Must be rejected or routed to explicit reversal/refund compensating workflow (never silent status flip).
   - **Cross-Tenant Ownership:** Aggregate commands must verify `entity.tenant_id == actor.tenant_id` before evaluating state.
