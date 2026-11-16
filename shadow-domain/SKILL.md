---
name: shadow-domain
description: "Domain-Driven Design & Business Invariant Modeling. Use when modeling complex state machines, approval/cancellation policies, bounded contexts, aggregate consistency boundaries, domain events, or anti-corruption layers. Do NOT use for simple CRUD screens (keep lightweight), stakeholder PRD interviews (shadow-discovery), physical DB tuning (shadow-db), or system topology/C4 (shadow-architect)."
---

# `/shadow-domain` — Domain-Driven Design & Business Invariant Modeling

- **Owner:** Bounded contexts, ubiquitous language, aggregate consistency boundaries, state transitions, and executable invariants.
- **Boundaries:** Stakeholder PRD elicitation (`shadow-discovery`), physical SQL indexing (`shadow-db`), system topology/containers (`shadow-architect`).

## 1. Preconditions, DDD Applicability Limits & Escalation
- **Anti-Overengineering Rule:** Never introduce heavy DDD ceremony (aggregates, event sourcing, value-object wrappers) for simple CRUD tables without stateful invariants.
- **Ambiguity Escalation Rule:** If two domain policies conflict (e.g., whether an already-settled invoice can be cancelled), **STOP and escalate** the conflict instead of inventing an unstated policy.

## 2. 6-Step Domain Modeling Playbook
Read [`methodologies/DDD-BOUNDED-CONTEXTS-AND-AGGREGATES.md`](methodologies/DDD-BOUNDED-CONTEXTS-AND-AGGREGATES.md) and [`playbooks/INVARIANT-CATALOG-AND-STATE-SPEC.md`](playbooks/INVARIANT-CATALOG-AND-STATE-SPEC.md):
1. **Gather Real Business Scenarios:** Walk through happy, concurrent, and cancellation/reversal edge scenarios.
2. **Build Ubiquitous Glossary & Conflict Register:** Resolve overlapping terms (`Order` vs `Invoice` vs `Shipment`) across teams.
3. **Define State Diagrams & Invariants:** List illegal transitions (`COMPLETED -> CANCELLED`), concurrency rules (optimistic lock on aggregate root), and cross-tenant isolation.
4. **Delineate Bounded Contexts & Anti-Corruption Layers (ACL):** Keep core domain logic isolated from legacy external ERP/vendor schemas.
5. **Distinguish Domain Events vs Integration Events:** Internal aggregate facts vs versioned cross-context public contracts.
6. **Express Executable Acceptance Tests:** Enforce identical invariants across API validation, domain entity, and persistence layers.

## 3. Examples & Deterministic Verifier
- **Happy Path:** Approval workflow validates `PENDING -> APPROVED` with maker != checker invariant and optimistic `version` check.
- **Ambiguous / Must-Reject:** Ambiguous cancellation rule resolved by guessing silently instead of escalating, or applying full DDD aggregates to a 3-column lookup table -> **BLOCKED** by `domain_invariant_verifier.py`.

```powershell
python "shadow-domain/scripts/domain_invariant_verifier.py" --self-test
python "shadow-domain/scripts/domain_invariant_verifier.py" --verify-model path/to/domain_model.json
```
