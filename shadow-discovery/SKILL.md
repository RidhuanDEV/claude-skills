---
name: shadow-discovery
description: Requirement elicitation, stakeholder mapping, functional/non-functional requirements (FR/NFR), scope boundaries, testable acceptance criteria (Given/When/Then), and contradiction/gap analysis before architecture or coding begins. Trigger with /shadow-discovery.
---

# Shadow Discovery (`/shadow-discovery`) — Requirement Engineering & Scope Gate (SDLC Stage 1)

Use this skill at the start of any new project, client brief, TOR/KAK analysis, or major feature request to transform raw, ambiguous client desires into a **contradiction-free, auditable, and testable specification** before writing code.

---

## 1. The Ambiguity Stop Rule (Quality Gate 1)

- **Never guess business rules that affect money, legal compliance, access control, or destructive state transitions.**
- Before proceeding to `/shadow-architect` or coding, inspect the raw input for:
  1. **Missing Actors / Roles**: Who performs the action, who approves it, and who can view/audit it?
  2. **Contradictory Rules**: Does Requirement A conflict with Requirement B or existing database invariants?
  3. **Undefined Edge Cases**: What happens on cancellation, refund, partial fulfillment, timeout, rejected approval, or duplicate submission?
  4. **Unbounded Scope ("Gold-Plating")**: Separate **In-Scope (MVP / Phase 1)** from **Out-of-Scope (Future Phase)** explicitly.

---

## 2. Mandatory Discovery Deliverables

When `/shadow-discovery` is executed, produce or update the following structured sections (compatible with `/shadow-doc` for `.docx` generation):

### A. Stakeholder & Actor Matrix
| Actor / Role | Core Responsibilities | Access Level & Tenant Scope | Key Pain Points / Goals |
| :--- | :--- | :--- | :--- |
| `Super Admin` | Global configuration, tenant provisioning | Cross-tenant (System) | Auditability & zero manual DB edits |
| `Client Operator` | Daily transaction entry & verification | Single-tenant (`tenant_id`) | Fast entry, clear validation errors |

### B. Functional Requirements (FR) with Testable Acceptance Criteria
Every Functional Requirement (`FR-MOD-001`) MUST have:
- **Priority**: `P0 (Must-Have)` | `P1 (Should-Have)` | `P2 (Nice-to-Have)`
- **Business Rule / Invariant**: Explicit formula, state transition (`DRAFT -> SUBMITTED -> APPROVED | REJECTED`), and validation constraints.
- **Given / When / Then Acceptance Criteria**: Directly traceable to `/shadow-uat` and `/shadow-test`.

### C. Non-Functional Requirements (NFR)
Explicitly quantify:
- **Performance & Scale**: Target concurrent users, peak RPS, max acceptable `p95` latency (`< 400ms`), and expected annual data volume growth.
- **Security & Compliance**: Authentication method, RBAC/ABAC granularity, PII encryption (UU PDP / ISO 27001 / OWASP ASVS level), and audit log retention.
- **Availability & Recovery**: Target SLA (`99.9%`), RPO (max tolerable data loss window, e.g. `< 15 min`), and RTO (max recovery time, e.g. `< 1 hour`).

### D. Gap Analysis & Clarifying Questions for Stakeholder
List open ambiguities in a prioritized table with a **Recommended Default** so the **Monarch** or client can approve or override with minimum friction.

---

## 3. Stage 1 Exit Gate Checklist (To Unlock `/shadow-architect`)
- [ ] In-Scope vs Out-of-Scope boundaries explicitly documented.
- [ ] All P0 requirements have deterministic Given/When/Then acceptance criteria.
- [ ] Zero unresolved contradictions between business rules.
- [ ] NFRs (concurrency, latency, security, RPO/RTO) quantified.
