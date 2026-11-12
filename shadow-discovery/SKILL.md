---
name: shadow-discovery
description: Requirement elicitation, stakeholder mapping, functional/non-functional requirements (FR/NFR), scope boundaries, testable acceptance criteria (Given/When/Then), and contradiction/gap analysis before architecture or coding begins. Trigger with /shadow-discovery.
---

# Shadow Discovery (`/shadow-discovery`) — Requirement Engineering & Scope Gate (SDLC Stage 1)

Use this skill at the start of any new project, client brief, TOR/KAK analysis, or major feature request to transform raw, ambiguous client desires into a **contradiction-free, auditable, and testable specification** before writing code.

---

## 1. The Ambiguity Stop Rule & Evidence Classification (Quality Gate 1)

- **Never guess business rules that affect money, legal compliance, access control, or destructive state transitions.**
- **Mandatory Evidence Classification**: Every discovery claim must be tagged as `[EVIDENCE]` (grounded in repo code, tickets, analytics, or dated interviews), `[ASSUMPTION]` (with risk & validation plan), `[PROPOSAL]`, or `[NEEDS VALIDATION]`. Never invent fake user research or personas.
- **The Five Foundational Strategy Questions** ([`ghaida-intent/skills/strategize/SKILL.md`](file:///d:/Ridhuan%20Ngoding%20Moment/SKILL/shadow-design/references/external-upstreams/ghaida-intent/skills/strategize/SKILL.md)):
  1. *Problem Validation*: Is this a real, recurring problem worth solving?
  2. *Audience Definition*: Who experiences it most acutely, and in what context?
  3. *Solution Fit*: Why does this mechanism solve the root cause rather than a symptom?
  4. *Feature Validation*: What is the smallest testable slice (MVP) that proves value?
  5. *Competitive & Existing System Landscape*: How is it solved today in the codebase or market?
- Before proceeding to `/shadow-architect` or coding, inspect the raw input for:
  1. **Missing Actors / Roles**: Who performs the action, who approves it, and who can view/audit it?
  2. **Contradictory Rules**: Does Requirement A conflict with Requirement B or existing database invariants?
  3. **Undefined Edge Cases**: What happens on cancellation, refund, partial fulfillment, timeout, rejected approval, or duplicate submission?
  4. **Unbounded Scope ("Gold-Plating")**: Separate **In-Scope (MVP / Phase 1)** from **Out-of-Scope (Future Phase)** explicitly.

---

## 1b. Foreign-Key Reference Routing (PM Discovery, Strategy & Research Packs)

Load only the specific reference file needed for deep discovery or strategic framing:
- **Evidence & JTBD Framing**: [`shadow-design/references/ai-product-designer-skill-pack/01-discovery-and-evidence.md`](file:///d:/Ridhuan%20Ngoding%20Moment/SKILL/shadow-design/references/ai-product-designer-skill-pack/01-discovery-and-evidence.md)
- **Assumption Identification & Prioritization (`Value | Usability | Viability | Feasibility | Ethics`)**: [`identify-assumptions-existing/SKILL.md`](file:///d:/Ridhuan%20Ngoding%20Moment/SKILL/shadow-design/references/external-upstreams/pm-skills/pm-product-discovery/skills/identify-assumptions-existing/SKILL.md), [`identify-assumptions-new/SKILL.md`](file:///d:/Ridhuan%20Ngoding%20Moment/SKILL/shadow-design/references/external-upstreams/pm-skills/pm-product-discovery/skills/identify-assumptions-new/SKILL.md) & [`prioritize-assumptions/SKILL.md`](file:///d:/Ridhuan%20Ngoding%20Moment/SKILL/shadow-design/references/external-upstreams/pm-skills/pm-product-discovery/skills/prioritize-assumptions/SKILL.md)
- **Opportunity Solution Tree & Experiment Design (XYZ Hypothesis / Pretotyping)**: [`opportunity-solution-tree/SKILL.md`](file:///d:/Ridhuan%20Ngoding%20Moment/SKILL/shadow-design/references/external-upstreams/pm-skills/pm-product-discovery/skills/opportunity-solution-tree/SKILL.md), [`brainstorm-experiments-existing/SKILL.md`](file:///d:/Ridhuan%20Ngoding%20Moment/SKILL/shadow-design/references/external-upstreams/pm-skills/pm-product-discovery/skills/brainstorm-experiments-existing/SKILL.md) & [`brainstorm-experiments-new/SKILL.md`](file:///d:/Ridhuan%20Ngoding%20Moment/SKILL/shadow-design/references/external-upstreams/pm-skills/pm-product-discovery/skills/brainstorm-experiments-new/SKILL.md)
- **PRD Authoring & Red-Team PRD Stress Test**: [`pm-execution/skills/create-prd/SKILL.md`](file:///d:/Ridhuan%20Ngoding%20Moment/SKILL/shadow-design/references/external-upstreams/pm-skills/pm-execution/skills/create-prd/SKILL.md) & [`pm-execution/commands/red-team-prd.md`](file:///d:/Ridhuan%20Ngoding%20Moment/SKILL/shadow-design/references/external-upstreams/pm-skills/pm-execution/commands/red-team-prd.md)
- **Primary User Research & Synthesis**: [`ghaida-intent/skills/investigate/SKILL.md`](file:///d:/Ridhuan%20Ngoding%20Moment/SKILL/shadow-design/references/external-upstreams/ghaida-intent/skills/investigate/SKILL.md) & [`designer-skills/design-research/README.md`](file:///d:/Ridhuan%20Ngoding%20Moment/SKILL/shadow-design/references/external-upstreams/designer-skills/design-research/README.md)

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

### D. Assumption Risk Matrix & Clarifying Questions for Stakeholder
Map unverified assumptions across **5 Risk Dimensions** (*Value, Usability, Viability, Feasibility, Ethics*), and list open ambiguities in a prioritized table with a **Recommended Default** so the **Monarch** or client can approve or override with minimum friction.

---

## 3. Stage 1 Exit Gate Checklist (To Unlock `/shadow-architect`)
- [ ] In-Scope vs Out-of-Scope boundaries explicitly documented.
- [ ] Every product/UX claim tagged (`[EVIDENCE]`, `[ASSUMPTION]`, `[PROPOSAL]`, `[NEEDS VALIDATION]`).
- [ ] High-risk assumptions (*Value, Usability, Viability, Feasibility, Ethics*) identified with validation plans.
- [ ] All P0 requirements have deterministic Given/When/Then acceptance criteria.
- [ ] Zero unresolved contradictions between business rules (Red-Team PRD check passed).
- [ ] NFRs (concurrency, latency, security, RPO/RTO) quantified.
