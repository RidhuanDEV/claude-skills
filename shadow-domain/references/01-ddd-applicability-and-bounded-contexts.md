# 01. DDD Applicability & Bounded Contexts

## 1. Purpose & Activation Conditions
Determine objectively when Domain-Driven Design (DDD) adds value versus when thin CRUD is superior, resolve ambiguous ubiquitous-language terms across teams, and draw clean Bounded Context boundaries. Load before introducing DDD aggregates/bounded contexts or resolving terminology conflicts across services.

## 2. Prerequisites
- Real business scenarios (happy, concurrent, reversal, cancellation) gathered with stakeholders (`/shadow-discovery`).

## 3. Technical Principles & Constraints
- **Anti-Overengineering Rule (Right-Sized DDD):** NEVER introduce heavy DDD ceremony (Aggregate Roots, Value Object wrappers, Repositories, Event Sourcing) for simple 3-column lookup tables, static settings, or stateless CRUD forms! Match modeling weight strictly to **stateful invariant complexity**:
  - Lookup / Reference CRUD -> Thin Service / Transaction Script
  - Pure Stateless Calculations (tax, fee, pricing math) -> Pure Domain Service
  - Multi-Field State Machines, Money, Approvals, Quotas, Scheduling -> Aggregate Root + Explicit FSM (`02`, `03`)
- **Ubiquitous Language & Conflict Register:** Words like `Order`, `Invoice`, `Customer`, `Schedule`, or `Driver` mean subtly different things across Sales, Finance, and Operations. Record an explicit **Glossary + Policy Conflict Register**.
- **Ambiguity Escalation Gate (NEVER Guess Silent Policies!):** When two domain rules conflict or an edge policy is unstated (e.g., `"Can a settled invoice be cancelled?"`, `"Does swapping a driver retroactively rewrite yesterday's completed shift log?"`), **STOP and escalate** the exact trade-off to the Monarch / domain owner instead of silently inventing behavior!
- **Bounded Context Ownership:** Each Bounded Context owns its own model, terminology, and database tables — cross-context interaction happens ONLY through explicit versioned contracts or Anti-Corruption Layers (`04`), never raw cross-context table joins!

## 4. Architecture & Implementation
```typescript
export type ModelingComplexity = 'simple_crud' | 'pure_rules' | 'stateful_invariants';

export interface SubdomainAssessment {
  readonly name: string;
  readonly hasMultiFieldInvariants: boolean;
  readonly hasNonTrivialStateMachine: boolean;
  readonly handlesMoneyOrCompliance: boolean;
  readonly hasUnresolvedPolicyConflict: boolean;
}

export function recommendDomainPattern(
  sub: SubdomainAssessment
): { readonly pattern: ModelingComplexity | 'STOP_ESCALATE_POLICY_CONFLICT'; readonly rationale: string } {
  if (sub.hasUnresolvedPolicyConflict) {
    return {
      pattern: 'STOP_ESCALATE_POLICY_CONFLICT',
      rationale: `Resolve conflicting business policy in '${sub.name}' with domain owner before modeling.`,
    };
  }
  if (sub.hasNonTrivialStateMachine || sub.handlesMoneyOrCompliance || sub.hasMultiFieldInvariants) {
    return {
      pattern: 'stateful_invariants',
      rationale: `Use Aggregate Root + Explicit FSM + Optimistic Locking for '${sub.name}'.`,
    };
  }
  return {
    pattern: 'simple_crud',
    rationale: `Keep '${sub.name}' lightweight (validated schema + thin service); avoid cargo-cult DDD.`,
  };
}
```
Offline model validation:
```powershell
python "shadow-domain/scripts/domain_invariant_verifier.py" --self-test
python "shadow-domain/scripts/domain_invariant_verifier.py" --verify-model path/to/domain_model.json
```

## 5. Platform / Vendor Variations
| Context Relationship (DDD Context Map) | Pattern | When to Apply |
| :--- | :--- | :--- |
| **Upstream Legacy ERP / Gov API -> Core App** | **Anti-Corruption Layer (ACL)** | Isolate dirty external status codes/schemas from polluting core domain enums |
| **Core Domain -> Downstream Notifications/Billing** | **Published Language (Versioned Integration Event)** | Decouple via Transactional Outbox (`shadow-concurrency`) |
| **Two Tightly Coupled Internal Modules** | **Modular Monolith Boundary** (`shadow-architect`) | Share deployment unit while forbidding cross-module internal table imports |

## 6. Decision Matrix & Trade-Offs
| Subdomain Example | Right Pattern | Avoid |
| :--- | :--- | :--- |
| Country / Tag / Category Table | Thin CRUD + Schema Validation | Aggregate Root + Event Sourcing |
| PPN / Discount / Proration Calculator | Pure Stateless Domain Service | Scattering math across UI & controllers |
| Purchase Order Approval / Fleet Dispatch Schedule | Aggregate Root + Explicit FSM + CAS | Direct `db.update({ status: req.body.status })` |

## 7. Real Production Scenario
A fleet scheduling system reuses a single `Schedule` model across Booking, Payroll, and Live Dispatch. When Operations swaps a replacement driver on a backdated trip, Payroll's historical driver payout calculation silently flips because both contexts mutated the same mutable row without context boundaries or backdating policy. Splitting `DispatchAssignment` (operational) from `SettledPayrollLedger` (immutable financial snapshot via ACL/event) and escalating the backdated-swap rule to the business owner eliminates silent payroll corruption.

## 8. Failure Modes & Edge Cases
- **WRONG:** Inventing 8 abstract DDD layers (`ValueObject`, `AggregateFactory`, `DomainEventBus`) for a static `faq_items` CRUD table.
- **RIGHT:** Apply `recommendDomainPattern` — reserve aggregates and FSMs strictly for stateful invariants.
- **WRONG:** Silently deciding `"I'll allow cancelling a PAID order and auto-refunding it"` when the business spec never specified refund authorization rules.
- **RIGHT:** Flag the ambiguity explicitly, pause implementation of that transition, and request domain owner sign-off.

## 9. Testing & Verification
- Run `python shadow-domain/scripts/domain_invariant_verifier.py --self-test` and `python -m unittest discover -s shadow-domain/tests -v`.
- Verify every ambiguous or conflicting policy is logged in the Conflict Register and blocked by the verifier until resolved.

## 10. Operational Considerations
- Keep the Ubiquitous Glossary concise (1 page in `docs/domain/glossary.md`) and enforce identical naming across TypeScript types, OpenAPI schemas, and database columns.

## 11. Authoritative References
- Eric Evans — *Domain-Driven Design Reference* (`https://www.domainlanguage.com/ddd/reference/`).
- Vaughn Vernon — *Implementing Domain-Driven Design* (Bounded Contexts & Context Mapping).

## 12. Limitations & When NOT to Use
- DDD strategic patterns do NOT fix unclear business requirements (`shadow-discovery`) or poor SQL indexing (`shadow-db`); use DDD strictly where business-rule consistency is the true complexity driver.
