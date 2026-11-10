---
name: shadow-plan
description: Decompose PRD/SRS and Architecture Specs into Epics, User Stories, Technical Tasks, Dependency Graphs, Milestones, Definition of Ready (DoR), Definition of Done (DoD), and Effort Estimations. Trigger with /shadow-plan.
---

# Shadow Plan (`/shadow-plan`) — Task Decomposition & Delivery Roadmap (SDLC Stage 2 -> 3 Bridge)

Use this skill to translate approved requirements (`/shadow-discovery`) and system architecture (`/shadow-architect`) into an executable, dependency-ordered engineering backlog.

---

## 1. Work Breakdown Hierarchy (`Epic -> Story -> Task`)

1. **Epics (`EPIC-01`)**: High-level business capability or module (e.g., *Identity & Multi-Tenant RBAC*, *Order & Approval Workflow*, *Executive Reporting & Export*).
2. **User Stories (`US-01.1`)**: Vertical slice delivering verifiable value, mapped 1-to-1 or 1-to-many with `FR-*` IDs from `/shadow-discovery`.
3. **Technical Tasks (`TASK-01.1.A`)**: Concrete layer implementation steps:
   - `[DB]` Schema migration & seed (`/shadow-data`)
   - `[API]` Backend service, validation, controller & OpenAPI/Postman sync (`/shadow-api`)
   - `[UI]` Frontend screen, responsive mobile layout & state wiring (`antislop` + `/shadow-cache`)
   - `[QA]` Automated unit/integration tests (`/shadow-test`) & E2E verification (`/shadow-browser`)

---

## 2. Dependency Graph & Critical Path

Always provide a Mermaid `flowchart LR` dependency graph showing execution waves so foundational tasks never block downstream features:
- **Wave 0 (Foundation)**: `/shadow-bootstrap` + `/shadow-auth` + core DB migrations (`/shadow-data`).
- **Wave 1 (Core Master Data & CRUD)**: Primary domain entities and reference tables.
- **Wave 2 (Core Transactions & Workflows)**: State machines, approvals, and external integrations (`/shadow-integrate`).
- **Wave 3 (Reporting, Dashboards & Exports)**: Aggregations, Data Warehouse/ETL (`/shadow-db`), and document exports (`/shadow-doc`).
- **Wave 4 (Pre-UAT Hardening, Staging UAT & Release)**: `/shadow-quality`, `/shadow-sec`, `/shadow-perf`, `/shadow-uat`, `/shadow-release`, `/shadow-handover`.

---

## 3. Mandatory Governance Gates: DoR & DoD

### Definition of Ready (DoR — Required Before Starting Any Story)
- [ ] Requirement ID (`FR-*`) and Given/When/Then acceptance criteria are locked.
- [ ] Database schema impact and API endpoint contract are defined.
- [ ] UI states (*Loading*, *Empty*, *Error*, *Success*, *Forbidden*) are specified.
- [ ] Blocking upstream tasks are completed.

### Definition of Done (DoD — Required Before Marking Any Story Complete)
- [ ] Code adheres to strict typing (`0 any`, `0 as Type` casting) and zero dead code.
- [ ] Backend endpoints updated in `openapi.yaml` and `postman_collection.json` (`/shadow-api`).
- [ ] Automated unit & integration tests (`/shadow-test`) pass (`100%` green on happy path, 400/401/403/404/409/422).
- [ ] Responsive UI verified at `375px` mobile and `1440px` desktop (`/shadow-browser` + `antislop`).
- [ ] Lint, typecheck, and build succeed with zero errors (`/shadow-quality`).
