---
name: shadow-domain
description: "Use when modeling business invariants, state transitions, aggregates, cancellation, or bounded contexts. Not for simple CRUD."
---

# Shadow Domain (`/shadow-domain`) — DDD, State Machines & Business Invariants

- **Owner:** Bounded contexts, ubiquitous language, aggregate consistency boundaries, explicit state machines, anti-corruption layers, and executable invariants.
- **Boundaries:** Stakeholder PRD elicitation (`/shadow-discovery`), physical SQL indexing (`/shadow-db`), system topology/C4 (`/shadow-architect`), async queue durability (`/shadow-concurrency`).

## 1. Preconditions, Anti-Overengineering & Escalation Rules

1. **Anti-Overengineering Rule:** Never introduce heavy DDD ceremony (Aggregate Roots, Value Objects, Event Sourcing) for simple lookup tables or stateless CRUD without invariants.
2. **Ambiguity Escalation Rule:** If two business policies conflict (e.g., cancelling a settled invoice or backdating a completed shift), **STOP and escalate** the conflict to the domain owner/Monarch instead of silently guessing.
3. **Closed FSM & Optimistic CAS:** Express state transitions in a closed `ALLOWED_TRANSITIONS` map, enforce maker-checker (`approverId !== requesterId`), keep monetary totals in integer minor units, and persist mutations with `WHERE id = $1 AND tenant_id = $2 AND version = $3`.
4. **Domain vs Integration Events & ACL:** Emit versioned integration events via Transactional Outbox strictly inside DB commit; translate external vendor/ERP payloads through fail-closed Anti-Corruption Layers.

## 2. 6-Step Domain Modeling Playbook & Verifier

Read [`methodologies/DDD-BOUNDED-CONTEXTS-AND-AGGREGATES.md`](methodologies/DDD-BOUNDED-CONTEXTS-AND-AGGREGATES.md) and [`playbooks/INVARIANT-CATALOG-AND-STATE-SPEC.md`](playbooks/INVARIANT-CATALOG-AND-STATE-SPEC.md), then verify models offline (`L0`/`L1`):
```powershell
python "shadow-domain/scripts/domain_invariant_verifier.py" --self-test
python "shadow-domain/scripts/domain_invariant_verifier.py" --verify-model path/to/domain_model.json
python -m unittest discover -s "shadow-domain/tests" -v
```
Graded specialist scenarios live in [evaluations.md](evaluations.md) (7 scenarios including backdated schedule swaps, CRUD anti-overengineering, policy conflict escalation, maker-checker, and ACL fail-closed handling).

## Reference Guide

Load **only** the 1–2 modules matching the active subtask (never load all 4 at once):

| Task / Scenario | Tier | Load Reference |
| :--- | :--- | :--- |
| DDD vs thin CRUD decision matrix, ubiquitous glossary, ambiguity escalation & bounded contexts | CORE | [references/01-ddd-applicability-and-bounded-contexts.md](references/01-ddd-applicability-and-bounded-contexts.md) |
| Small aggregate boundaries, multi-tenant & integer-money invariants, optimistic `version` CAS | CORE | [references/02-aggregates-invariants-and-optimistic-locking.md](references/02-aggregates-invariants-and-optimistic-locking.md) |
| Closed FSM `ALLOWED_TRANSITIONS`, maker-checker approvals, backdating & cancellation guards | CORE | [references/03-finite-state-machines-and-cancellation-policies.md](references/03-finite-state-machines-and-cancellation-policies.md) |
| Domain vs versioned integration events (Outbox), fail-closed ACL adapters & property/FSM testing | ADVANCED | [references/04-domain-events-acl-and-invariant-testing.md](references/04-domain-events-acl-and-invariant-testing.md) |

Do not load unrelated references unnecessarily.
