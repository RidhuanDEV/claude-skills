---
name: shadow-plan
description: Decompose PRD/SRS and Architecture Specs into Epics, User Stories, Technical Tasks, Dependency Graphs, Milestones, Definition of Ready (DoR), Definition of Done (DoD), and Effort Estimations. Trigger with /shadow-plan.
---

# Shadow Plan (`/shadow-plan`) — Task Decomposition & Delivery Roadmap (SDLC Stage 2 -> 3 Bridge)

Use this skill to translate approved requirements (`/shadow-discovery`) and system architecture (`/shadow-architect`) into an executable, dependency-ordered engineering backlog.

---

## 1. Work Breakdown Hierarchy & End-to-End Traceability (`EPIC -> FR -> US/JOB -> FLOW -> SCR/STATE -> AC -> TASK -> TEST -> METRIC`)

> **Foreign-Key Reference Routing**:
> - **User Stories & Job Stories (JTBD)**: [`pm-execution/skills/user-stories/SKILL.md`](file:///d:/Ridhuan%20Ngoding%20Moment/SKILL/shadow-design/references/external-upstreams/pm-skills/pm-execution/skills/user-stories/SKILL.md) & [`pm-execution/skills/job-stories/SKILL.md`](file:///d:/Ridhuan%20Ngoding%20Moment/SKILL/shadow-design/references/external-upstreams/pm-skills/pm-execution/skills/job-stories/SKILL.md)
> - **Pre-Mortem Risk Analysis (`Tigers | Paper Tigers | Elephants`)**: [`pm-execution/skills/pre-mortem/SKILL.md`](file:///d:/Ridhuan%20Ngoding%20Moment/SKILL/shadow-design/references/external-upstreams/pm-skills/pm-execution/skills/pre-mortem/SKILL.md)
> - **Outcome Roadmap & Sprint Planning**: [`pm-execution/skills/outcome-roadmap/SKILL.md`](file:///d:/Ridhuan%20Ngoding%20Moment/SKILL/shadow-design/references/external-upstreams/pm-skills/pm-execution/skills/outcome-roadmap/SKILL.md) & [`pm-execution/skills/sprint-plan/SKILL.md`](file:///d:/Ridhuan%20Ngoding%20Moment/SKILL/shadow-design/references/external-upstreams/pm-skills/pm-execution/skills/sprint-plan/SKILL.md)
> - **Traceability & Design Ops Handoff**: [`10-handoff-and-measurement.md`](file:///d:/Ridhuan%20Ngoding%20Moment/SKILL/shadow-design/references/ai-product-designer-skill-pack/10-handoff-and-measurement.md) & [`designer-skills/design-ops/skills/handoff-spec/SKILL.md`](file:///d:/Ridhuan%20Ngoding%20Moment/SKILL/shadow-design/references/external-upstreams/designer-skills/design-ops/skills/handoff-spec/SKILL.md)

1. **Epics (`EPIC-01`)**: High-level business capability or outcome module (e.g., *Identity & Multi-Tenant RBAC*, *Order & Approval Workflow*, *Executive Reporting & Export*).
2. **User Stories (`US-01.1`) & Job Stories (`JOB-01.1`)**:
   - Use **User Stories** (`As a <role>, I want <capability>, so that <measurable outcome>`) when role permissions drive behavior.
   - Use **Job Stories** (`When <situational trigger>, I want to <motivation/action>, so I can <expected outcome>`) when context/urgency drives behavior.
   - Preserve stable IDs (`US-ID -> FLOW-ID -> SCR-ID / STATE-ID -> AC-ID -> TASK-ID -> TEST-ID -> METRIC-ID`) across revisions (`CONFIRMED | PROPOSED | UNKNOWN | DEFERRED`).
3. **Technical Tasks (`TASK-01.1.A`)**: Concrete layer implementation steps:
   - `[DB]` Schema migration & seed (`/shadow-data`)
   - `[API]` Backend service, validation, controller, async `HTTP 202` contract & OpenAPI/Postman sync (`/shadow-api`)
   - `[UI]` Frontend screen, 9-state machine (`Initial, Empty, Loading, Partial, Success, Validation Error, 403 Denied, Offline, 409/ETag Conflict`), responsive mobile layout & state wiring (`/shadow-design` + `antislop` + `/shadow-cache`)
   - `[QA]` Automated unit/integration tests with ephemeral Docker teardown (`/shadow-test`) & E2E verification (`/shadow-browser`)
4. **Pre-Mortem Risk Table (Before Wave Execution)**:
   Classify delivery and architectural risks into:
   - **Tigers**: Genuine, high-probability/high-impact threats requiring immediate design/code mitigation before coding.
   - **Paper Tigers**: Loud concerns that appear scary but have low actual impact or are already mitigated.
   - **Elephants**: Unspoken organizational, data-quality, or legacy-system truths that the team might avoid discussing.

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
- [ ] Requirement ID (`FR-*`), `US-ID`, and Given/When/Then acceptance criteria (`AC-ID`) are locked.
- [ ] Database schema impact, API endpoint contract, and async behavior (`HTTP 200/201` vs `HTTP 202 Accepted` queued/processing) are defined.
- [ ] All **9 UI States** (*Initial, Empty [No-Data / No-Results / Error], Loading, Partial, Success, Validation Error, 403 Permission-Denied, Offline, and 409/ETag Stale Conflict*) are specified (`/shadow-design`).
- [ ] Pre-Mortem *Tigers* and *Elephants* have assigned mitigations and owners.
- [ ] Blocking upstream tasks are completed.

### Definition of Done (DoD — Required Before Marking Any Story Complete)
- [ ] Code adheres to strict typing (`0 any`, `0 as Type` casting) and zero dead code (`shadow_gate.py`).
- [ ] Backend endpoints updated in `openapi.yaml` and `postman_collection.json` (`/shadow-api`).
- [ ] Automated unit & integration tests (`/shadow-test`) pass (`100%` green on happy path, 400/401/403/404/409/422) with zero leftover ephemeral Docker test containers/images (`--check-docker-leaks`).
- [ ] Responsive UI verified at `320px/375px` mobile and `1440px` desktop + `200%` zoom across all 9 states (`/shadow-browser` + `antislop`).
- [ ] Lint, typecheck, and build succeed with zero errors (`/shadow-quality`).
