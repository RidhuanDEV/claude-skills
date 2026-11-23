---
name: shadow-architect
description: "Single-System Architecture & Design. Use when designing one application architecture, C4 Mermaid diagrams, ADRs, module public facades, architectural fitness functions, capacity sizing, brownfield convention preservation, or deciding Monolith vs Modular Monolith vs Workers vs Microservices. Do NOT use for multi-app enterprise portfolios or 6-Domain SPBE (/shadow-ea)."
---

# Shadow Architect (`/shadow-architect`) — Single-System Architecture, C4/ADRs & Boundary Gate (SDLC Stage 2)

Use this skill after `/shadow-discovery` (or when evaluating structural changes) to establish a maintainable, right-sized architecture before scaffolding or coding.

- **Owner:** Application topology selection (Modular Monolith + Async Worker default), strict Mermaid C4 diagrams & ADRs, explicit ACID vs eventual consistency models, `public.ts` module facades & CI fitness functions, baseline capacity sizing, brownfield 10-facet convention preservation, and Official-First 8-field technology Decision Records.
- **Boundaries:** Multi-application enterprise portfolios & 6-Domain SPBE (`shadow-ea`), behavior-preserving legacy module cleanup (`shadow-refactor`), legacy due-diligence & rewrite TCO (`shadow-modernize`), greenfield CLI generator execution (`shadow-bootstrap`), and physical SQL indexing/tuning (`shadow-db`).

## Reference Guide

Load ONLY the 1–2 modular playbooks needed for the active architecture subtask:

| Module | Topic | Load When |
| :--- | :--- | :--- |
| [01-topology-selection-and-modular-monolith.md](references/01-topology-selection-and-modular-monolith.md) | Monolith vs Modular Monolith vs Async Worker vs Microservices, 4 evidence-based extraction triggers, decision-scope sizing | Choosing system topology or deciding whether to split a service/worker |
| [02-c4-diagrams-adrs-and-consistency-models.md](references/02-c4-diagrams-adrs-and-consistency-models.md) | Strict Mermaid C4 Context/Container/Sequence diagrams, compact ADR template, explicit ACID vs eventual consistency & failure assumptions | Documenting system context, flows, consistency boundaries, or formal ADRs |
| [03-module-facades-fitness-functions-and-capacity.md](references/03-module-facades-fitness-functions-and-capacity.md) | Typed `public.ts` facades (zero cross-module SQL joins), CI fitness functions (`dependency-cruiser`/`import-linter`/`ArchUnit`), RPS/storage/RAM sizing | Enforcing clean module isolation or estimating baseline capacity |
| [04-brownfield-convention-preservation-and-official-first.md](references/04-brownfield-convention-preservation-and-official-first.md) | 10-facet discovery (`codebase_intelligence.py`), 5-level Convention Precedence, Official-First 5-tier hierarchy & 8-field Decision Record | Extending brownfield repos without unsolicited rewrites or unapproved infra bloat |
| [evals/decision-trials.md](evals/decision-trials.md) | Reviewer calibration trials (local extraction, cross-team ownership, capacity uncertainty) | Calibrating architecture scope proportionality |
| [evaluations.md](evaluations.md) | Graded specialist evaluation scenarios (`ARCH-EVAL-01..07`) | Auditing anti-microservice bloat, module facades, brownfield fidelity, and `/shadow-ea` boundary |

---

## 1. Core Architectural Philosophy: Right-Sized Engineering

1. **Default to a Modular Monolith (+ Async Worker):** Split into distributed microservices ONLY when proven by heterogeneous compute isolation, `25+` engineer release contention, `> 10x` scaling divergence, or strict regulatory isolation.
2. **Enforce Strict Module Boundaries:** Modules communicate exclusively via typed public facades (`public.ts`) or domain events — NEVER by joining another module's internal tables or importing `internal/*`. Enforce mechanically in CI via fitness functions.
3. **Trace Every NFR to Consistency & Failure Mechanisms:** Explicitly separate **strict ACID** (money, inventory, auth grants) from **eventual consistency** (search sync, BI projections, notifications), documenting network partition, timeout, and clock-skew assumptions.
4. **Calibrate Deliverables to Decision Scope:** For reversible module-local changes, answer concisely inline (precedent, transaction boundary, coupling, rollback). Reserve C4 diagrams and formal ADRs (`docs/adr/ADR-XXX-*.md`) for shared contracts, deployment boundaries, or data-ownership shifts.

---

## 2. Brownfield Preservation & Official-First Gate

- **Brownfield Discovery First (`L0`):** Run `python "shadow-quality/scripts/codebase_intelligence.py" discover --repo-dir . --write-profile` across all 10 facets (`docs/engineering/CODEBASE_CONVENTIONS.md`). Preserve existing working architectures (MVC, Feature-Based, etc.) using the 5-level Convention Precedence Hierarchy (`User/Security -> AGENTS.md -> Closest 1–3 Precedents -> Global Shadow -> AI default`). Never impose unsolicited rewrites!
- **Official-First 8-Field Decision Record:** Follow `Existing trusted -> Official SDK -> Verified package -> Justified small custom -> Approved replacement` (`shadow-monarch/reference/OFFICIAL-FIRST-DEPENDENCY-POLICY.md`), preserve local SSO SDKs, and obtain explicit Monarch approval before adding new frameworks or extra infrastructure (`Docker`, `Redis`, `Kafka`, microservices).

```powershell
python "shadow-quality/scripts/codebase_intelligence.py" discover --repo-dir . --write-profile
python -m unittest discover -s shadow-architect/tests -v
```
