# 03. Finite State Machines & Approval/Cancellation Policies

## 1. Purpose & Activation Conditions
Model stateful workflows (approvals, maker-checker, cancellations, refunds, dispatch schedules, backdating guards) using explicit, closed **Finite State Machines (FSMs)** so illegal transitions, double-approvals, and retroactive history corruption are impossible. Load when designing any status-driven entity workflow.

## 2. Prerequisites
- Resolved domain policy for every edge transition (escalate conflicts first per `01`) and Aggregate `version` guard (`02`).

## 3. Technical Principles & Constraints
- **Explicit Closed Transition Table (`ALLOWED_TRANSITIONS`):** Every stateful entity defines a single authoritative map of `(current_status, command) -> next_status`. Any transition NOT explicitly present is **denied by default** (`INVALID_STATE_TRANSITION`). Terminal states (`REJECTED`, `CANCELLED`, `SETTLED`, `VOID`) have `[]` outgoing transitions unless an explicit **compensated reversal** state (`REVERSED` / `REFUNDED`) is modeled!
- **Maker-Checker / Four-Eyes Invariant:** On regulated approvals (finance, procurement, permissions, disbursements), explicitly enforce `approverId !== requesterId` inside the pure domain transition AND record `(actorId, role, reason, decidedAt)` immutably!
- **Temporal & Backdating Invariants (Preventing History Corruption):** For schedules, shifts, attendance, and ledgers (e.g., swapping a replacement driver on a past/in-progress schedule), explicitly model the **time cutoff policy** (`nowMs < shift.startMs` vs `IN_PROGRESS` vs `COMPLETED`):
  - NEVER silently overwrite a `COMPLETED` historical assignment row — either block backdated edits (`IMMUTABLE_PAST_RECORD`) OR emit a separate audited **Adjustment / Superseding Record** preserving the original record for payroll/compliance audit!
- **Cancellation & Reversal Compensation Semantics:** Distinguishing `CANCEL_BEFORE_DISPATCH` (free state change) from `CANCEL_AFTER_SETTLEMENT` (triggers compensating refund/reversal Saga) prevents accidental financial loss!

## 4. Architecture & Implementation
```typescript
export type TripStatus = 'SCHEDULED' | 'IN_PROGRESS' | 'COMPLETED' | 'CANCELLED';

const TRIP_TRANSITIONS: Readonly<Record<TripStatus, readonly TripStatus[]>> = {
  SCHEDULED: ['IN_PROGRESS', 'CANCELLED'],
  IN_PROGRESS: ['COMPLETED', 'CANCELLED'],
  COMPLETED: [], // Terminal: historical completed trips are immutable!
  CANCELLED: [],
};

export interface DriverSchedule {
  readonly id: string;
  readonly tenantId: string;
  readonly driverId: string;
  readonly status: TripStatus;
  readonly scheduledStartMs: number;
  readonly version: number;
}

export type ReassignOutcome =
  | { readonly ok: true; readonly next: DriverSchedule; readonly auditEvent: 'DRIVER_REASSIGNED' }
  | { readonly ok: false; readonly code: 'VERSION_CONFLICT' | 'BACKDATING_IMMUTABLE_HISTORY' | 'SAME_DRIVER' | 'TERMINAL_STATUS' };

export function reassignScheduleDriver(
  schedule: DriverSchedule,
  replacementDriverId: string,
  nowMs: number,
  expectedVersion: number
): ReassignOutcome {
  if (schedule.version !== expectedVersion) return { ok: false, code: 'VERSION_CONFLICT' };
  if (schedule.status === 'COMPLETED' || schedule.status === 'CANCELLED') {
    return { ok: false, code: 'TERMINAL_STATUS' };
  }
  // Protect historical consistency: disallow silent retroactive swaps after trip has already started/passed
  if (schedule.status === 'IN_PROGRESS' || nowMs >= schedule.scheduledStartMs) {
    return { ok: false, code: 'BACKDATING_IMMUTABLE_HISTORY' };
  }
  if (schedule.driverId === replacementDriverId) return { ok: false, code: 'SAME_DRIVER' };
  return {
    ok: true,
    next: { ...schedule, driverId: replacementDriverId, version: schedule.version + 1 },
    auditEvent: 'DRIVER_REASSIGNED',
  };
}

export function canTransitionTrip(from: TripStatus, to: TripStatus): boolean {
  return TRIP_TRANSITIONS[from].includes(to);
}
```

## 5. Platform / Vendor Variations
| Workflow Pattern | Recommended Representation | Persistence Guard |
| :--- | :--- | :--- |
| **Linear / Branching Entity Status** | Pure TypeScript/Python `ALLOWED_TRANSITIONS` map + discriminated result | `CHECK (status IN (...))` + `UPDATE ... WHERE id = $1 AND status = $expected_from AND version = $v` |
| **Multi-Step Approval Chain (L1 -> L2 -> CFO)** | Explicit `approvals[]` state rows + maker-checker `actorId != requesterId` | Unique constraint `(entity_id, step_no)` + append-only approval log |
| **Long-Running Multi-Service Reversal** | Explicit `CANCELLING -> CANCELLED` intermediate state + Outbox Saga (`shadow-concurrency`) | Never mark `CANCELLED` before compensating refund/release confirms |

## 6. Decision Matrix & Trade-Offs
| Backdated Correction Need | Bad Approach | Correct Approach |
| :--- | :--- | :--- |
| Driver swapped 2 hours BEFORE trip | Overwrite with no audit log | `reassignScheduleDriver` (`SCHEDULED` only) + emit `DRIVER_REASSIGNED` audit |
| Driver actually changed AFTER trip completed | Mutate historical `driver_id` in place (corrupts past logs/payroll!) | Block direct mutation (`BACKDATING_IMMUTABLE_HISTORY`); create separate audited `ScheduleAdjustment` record! |

## 7. Real Production Scenario
A logistics dispatch app allows admins to edit `driver_id` on any schedule row via `PATCH /schedules/:id`. When a dispatcher accidentally swaps a replacement driver onto yesterday's completed route (backdating), the route's status resets to `SCHEDULED`, breaking driver payroll calculations and GPS compliance logs. Locking transitions via `TRIP_TRANSITIONS` + `reassignScheduleDriver` (rejecting edits on `COMPLETED`/`IN_PROGRESS`/past timestamps and routing post-facto corrections through an immutable `ScheduleAdjustment` record) prevents schedule corruption structurally.

## 8. Failure Modes & Edge Cases
- **WRONG:** Accepting arbitrary `status` strings directly from `req.body.status` in a generic `PATCH /orders/:id` endpoint (lets callers jump directly from `DRAFT` to `PAID`!).
- **RIGHT:** Expose explicit command endpoints/methods (`POST /orders/:id/submit`, `POST /orders/:id/approve`, `POST /orders/:id/cancel`) enforced by the closed FSM transition table.
- **WRONG:** Allowing a creator to approve their own high-value purchase order because `"they have the admin role"`.
- **RIGHT:** Enforce `approverId !== requesterId` inside the pure domain transition (and document any explicit single-user SMB exemption cleanly if approved by Monarch!).

## 9. Testing & Verification
- Generate an exhaustive **State Transition Matrix Unit Test** iterating over ALL `N × N` pairs of `(fromState, toState)` verifying every allowed edge succeeds and every forbidden edge returns `INVALID_STATE`!
- Run `python shadow-domain/scripts/domain_invariant_verifier.py --verify-model <model.json>` to check unreachable states, deadlocks, missing maker-checker, and conflicting rules offline.

## 10. Operational Considerations
- Persist a dedicated `state_transitions` audit table (`entity_id`, `from_status`, `to_status`, `actor_id`, `reason`, `occurred_at`) on critical business workflows so support and auditors reconstruct exact lifecycle timelines in seconds.

## 11. Authoritative References
- David Harel — *Statecharts: A Visual Formalism for Complex Systems*.
- Shadow Domain Playbook (`shadow-domain/playbooks/INVARIANT-CATALOG-AND-STATE-SPEC.md`).

## 12. Limitations & When NOT to Use
- Do NOT embed external HTTP calls or side effects inside pure FSM transition functions; return `{ nextState, domainEvents[] }` and execute side effects via Transactional Outbox after DB commit (`04`).
