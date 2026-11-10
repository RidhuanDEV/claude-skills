---
name: shadow-architect
description: System Design, C4 Architecture Diagrams (Context, Container, Component), Architecture Decision Records (ADR), Monolith vs Modular Monolith vs Microservices evaluation, Capacity Estimation, and NFR alignment. Trigger with /shadow-architect.
---

# Shadow Architect (`/shadow-architect`) — System Architecture & ADR Gate (SDLC Stage 2)

Use this skill after `/shadow-discovery` (or when evaluating major structural changes) to establish a maintainable, right-sized architecture before scaffolding or coding.

---

## 1. Core Architectural Philosophy: Right-Sized Engineering

1. **Default to a Modular Monolith** unless independent team scaling, heterogeneous compute (e.g., heavy GPU worker vs CRUD API), or strict regulatory isolation proves that distributed microservices are necessary.
2. **Enforce Strict Module Boundaries**: Modules communicate via explicit public service interfaces or domain events — never by reaching directly into another module's internal tables or private repositories.
3. **Trace Every NFR to an Architectural Mechanism**:
   - High read concurrency -> Read replicas + `/shadow-cache` (`Redis` / `TanStack Query`).
   - Slow/unreliable external third-party calls -> Asynchronous outbox/queue worker + `/shadow-integrate` circuit breaker.
   - Multi-client data isolation -> `/shadow-auth` tenant-scoped queries / PostgreSQL RLS.

---

## 2. Mandatory Architecture Deliverables

### A. C4 Model Diagrams (Strict Mermaid Syntax)
1. **Level 1 — System Context Diagram**: The application, primary user personas, and external third-party systems (Payment Gateway, SSO, SMTP, Government APIs).
2. **Level 2 — Container Diagram**: Web/Mobile clients, API Gateway/Reverse Proxy, Backend API, Background Worker, Primary DB, Cache (`Redis`), Object Storage (`S3`/`MinIO`), and Data Warehouse.
3. **Level 3 — Component & Data Flow Diagram**: Key sequence diagrams (`sequenceDiagram`) for critical flows (Authentication, Checkout/Approval, Webhook Ingestion).

### B. Capacity & Resource Sizing Estimation
Calculate concrete baseline estimates from `/shadow-discovery` NFRs:
- **Traffic**: Daily Active Users (DAU) -> Average RPS -> Peak RPS ($3\times$ average).
- **Storage**: Row size $\times$ records/day $\times$ 365 days $\times$ retention years + $30\%$ index overhead + object storage growth.
- **Compute & Memory**: vCPU and RAM sizing for App Servers, Database (`shared_buffers` = 25% RAM), and Redis cache.

### C. Architecture Decision Records (`docs/adr/ADR-XXX-*.md`)
For every consequential choice (Database engine, Monolith vs Microservices, Auth strategy, Queue broker, Deployment target), record:
- **Status**: `Proposed | Accepted | Superseded`
- **Context & Problem Statement**
- **Options Considered (with Pros, Cons, and Cost/Operational Complexity)**
- **Decision & Rationale**
- **Consequences & Trade-offs**

---

## 3. Brownfield Architecture & Convention Preservation

When designing or extending an existing application (**Brownfield Project**):

### A. Brownfield vs Greenfield Project Routing
- **Greenfield**: Zero/empty repository. Proceed with standard Shadow Army scaffolding (`/shadow-bootstrap`) and right-sized Modular Monolith baseline.
- **Brownfield**: Existing codebase present. **Preserve existing architectural patterns** (Layered MVC, Feature-based, Hexagonal, Clean, Minimalist). Do **NOT** impose unsolicited architectural migrations (e.g. converting a working MVC into Clean Architecture/DDD) solely because it is perceived as "cleaner" or "more modern".

### B. Mandatory Existing-Codebase Discovery & Convention Profile
Before proposing architectural modifications, inspect the codebase across the **10 Discovery Facets** and maintain the Project Convention Profile at `docs/engineering/CODEBASE_CONVENTIONS.md`:
1. **Framework, Language & Runtime**: Exact version, module system (CommonJS vs ESM).
2. **Project Structure & Module Boundaries**: Directory organization, monorepo workspaces.
3. **Architectural Patterns**: Prevailing architectural style and layer boundaries.
4. **Naming Conventions**: File, folder, class, function, and variable casings.
5. **Code Formatting & Lint Rules**: Linter configs, indentation, quotes, trailing commas.
6. **API & Database Access Patterns**: Established ORM, query builders, repository patterns.
7. **Error Handling & Validation**: Centralized error middleware, validation libraries (Zod, Joi, FormRequest).
8. **Authentication & Authorization**: Session/JWT mechanisms, RBAC/ABAC guards.
9. **State Management & Caching**: Frontend stores (Zustand, Redux, Pinia), Redis caching keys.
10. **Testing & Dependency Conventions**: Test runners, mock styles, fixture conventions.

Run deterministic discovery and profiling:
```powershell
python "shadow-quality/scripts/codebase_intelligence.py" discover --repo-dir . --write-profile
```
If patterns conflict across legacy modules, **document the ambiguity** rather than inventing a global standard.

### C. Convention Precedence Hierarchy
Always resolve architectural decisions using this hierarchy:
1. **Level 1**: Explicit user requirements & safety/security constraints (SQL injection prevention, data isolation).
2. **Level 2**: Applicable project-level instructions (`AGENTS.md`, `CLAUDE.md`, documented architecture).
3. **Level 3**: Established patterns in relevant existing modules.
4. **Level 4**: Shadow Army global conventions.
5. **Level 5**: AI default preferences (**never** allowed to override established project conventions).

### D. Existing Code First Principle
- Always search for the closest existing implementation before architecting new components.
- Reuse existing services, utilities, middleware, and repositories.
- Match equivalent module structure and naming patterns across feature boundaries.

---

## 4. Stage 2 Exit Gate Checklist (To Unlock `/shadow-plan` & `/shadow-bootstrap`)
- [ ] C4 Context and Container diagrams validated in strict Mermaid syntax.
- [ ] Core database ERD (`/shadow-db`) and API contract strategy (`/shadow-api`) aligned with functional requirements.
- [ ] ADRs written for all critical stack and infrastructure choices.
- [ ] Capacity sizing confirms infrastructure fits client budget and SLA targets.
- [ ] For Brownfield projects: Project Convention Profile (`docs/engineering/CODEBASE_CONVENTIONS.md`) inspected and architectural preservation confirmed.
