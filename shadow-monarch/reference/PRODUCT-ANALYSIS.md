# PRODUCT-ANALYSIS — Product Management (PM), System Analyst (SA) & Business Analyst (BA)

Use when translating business goals or user needs into requirements, PRDs, BRDs, Functional/System Specifications
(FSD/SRS), user stories, acceptance criteria, system models, or impact analyses across IT projects.

## 1. Core principle: bridge business intent and engineering reality

- Requirements are contracts between stakeholders, designers, and engineers. Ambiguity in requirements becomes bugs
  in code.
- Always separate **Problem Space** (who is the user, what pain/goal do they have, why does it matter, how is success
  measured) from **Solution Space** (workflows, screens, APIs, data models, rules).
- Validate requirements against existing system architecture and data contracts when working in an existing repo.
  Never write specs that contradict verified domain invariants without flagging a migration/breaking change.

## 2. Discovery & scoping (PM / BA)

- **Objective & KPIs**: state the business goal, target user personas, success metrics (leading/lagging), and explicit
  **Non-Goals (Out of Scope)** to prevent scope creep.
- **Prioritization**: separate MVP / Must-Have (P0) from Should-Have (P1) and Nice-to-Have (P2) based on user value,
  technical dependency, compliance/risk, and effort.
- **Assumptions, dependencies & risks**: list external dependencies (third-party APIs, payment gateways, legal/PDP
  compliance, legacy DB constraints) and open questions requiring stakeholder sign-off.

## 3. Functional requirements & user stories

- **User Story format**: `As a <specific role/persona>, I want to <action/capability>, so that <measurable outcome>.`
- **Acceptance Criteria (AC)** — testable, unambiguous, covering happy path, edge cases, and negative/permission cases.
  Use **Gherkin (`Given / When / Then`)** or numbered rule tables:
  - *Happy path*: valid inputs, expected state transition, notifications/audit side effects.
  - *Validation & business rules*: exact field constraints (length, format, required/optional, uniqueness, calculation
    formulas, currency rounding).
  - *Authorization & role matrix*: CRUD/action permissions per role (`Admin`, `Reviewer`, `Applicant`, `Guest`, etc.).
  - *Failure & edge cases*: duplicate submission, concurrent edit, timeout/offline, partial failure, cancelled flow.

## 4. System analysis & modeling (SA)

Represent complex flows and structures visually with standard Mermaid diagrams alongside prose:
- **Business Process / User Flow**: `flowchart TD` or `flowchart LR` showing decision diamonds, actor swimlanes, and
  error branches.
- **Interaction & API Flow**: `sequenceDiagram` showing Actor → Frontend → API Gateway/Backend → DB → Queue/External
  Service, including sync vs async steps and error returns.
- **Lifecycle & State Machine**: `stateDiagram-v2` for entities with status transitions (e.g., `Draft → Submitted →
  UnderReview → Approved / Rejected`), explicitly listing **allowed transitions**, **triggering actors**, and **guards**.
- **Data Modeling**: `erDiagram` defining entities, primary/foreign keys, cardinality (`1:1`, `1:N`, `M:N` join tables),
  nullability, and ownership boundaries.

## 5. Data dictionary & API contract specification

When producing an FSD / SRS / Technical Spec:
- **Data Dictionary table**: `Field Name | Type | Required/Nullable | Default | Validation / Enum Values | Description`.
- **Endpoint Specification**: `Method & Path | Auth/Role | Request Params/Body | Response 2xx Envelope | Error Codes (400/401/403/404/409/422)`.
- Ensure field names, types, and nullability match the codebase's existing conventions (`camelCase` vs `snake_case`,
  ISO-8601 timestamps, integer minor units vs decimal money).

## 6. Change impact & traceability analysis

Before approving a requirement change on an existing system, map the blast radius:
1. **Database / Persistence**: new tables/columns, backfill needed, backward-compatible migration?
2. **Backend / Domain**: affected services, background jobs, cron schedules, webhooks, caches.
3. **API / Consumers**: breaking change for web frontend, mobile app versions in the wild, or partner integrations?
4. **Security & Compliance**: new PII fields, audit logging requirements, role permission changes.
5. **Requirement Traceability Matrix (RTM)**: map `Business Rule ID → User Story / FSD Section → API Endpoint / DB Table → Test Case ID`.

## 7. Non-functional requirements (NFR) checklist

Every specification must state applicable NFRs:
- **Performance & Scale**: expected RPS, peak concurrency, payload size limits, p95 latency targets.
- **Availability & Recovery**: SLA/uptime, RTO/RPO, retry/idempotency behavior when third parties fail.
- **Security & Privacy**: authentication method, RBAC/ABAC rules, PII masking, audit trail retention.
- **Compatibility & Localization**: supported browsers/devices, languages (e.g., Bahasa Indonesia & English), timezone/currency rules.

## 8. Anti-patterns

Vague criteria ("system should be fast and user-friendly") · happy-path-only specs with no error or permission states ·
undefined state transitions (how does an order get from `Pending` to `Cancelled`?) · UI wireframes treated as complete
backend business rules · changing DB schemas in specs without analyzing mobile/frontend consumer impact · mixing MVP
requirements with speculative future features without priority labels.
