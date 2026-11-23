# 01. Vertical Thin Slicing & End-to-End Story Traceability

## 1. Purpose & Activation Conditions
Use this playbook when decomposing approved PRD/SRS specifications (`/shadow-discovery`) and system architectures (`/shadow-architect`) into Epics, User Stories / Job Stories, and thin vertical technical tasks. Its objective is to guarantee every sprint increment ships working, testable end-to-end functionality rather than disconnected horizontal technical layers that fail during final-week integration.

Activate this playbook when:
- Breaking down a multi-screen or multi-module release into Sprint backlogs.
- Translating `FR-*` and `AC-*` requirements into runnable developer tasks across DB, API, UI, and QA.
- Reviewing an existing horizontal backlog (*"Sprint 1: all tables, Sprint 2: all endpoints, Sprint 3: all screens"*) and restructuring it into verifiable vertical increments.

## 2. Prerequisites
- Stage 1 Discovery Exit Gate passed (`/shadow-discovery`): locked `FR-*` IDs, quantified `NFR-*`, and 4-path Gherkin acceptance criteria (`AC-*`).
- Stage 2 Architecture boundaries approved (`/shadow-architect` / `/shadow-db` / `/shadow-design`): module contracts, data ownership, and applicable UI 9-state specifications.

## 3. Technical Principles & Constraints
1. **Vertical Thin Slices Over Horizontal Layers**: Every User Story (`US-*`) or Job Story (`JOB-*`) MUST cut cleanly from UI/trigger -> API/service -> persistence -> automated verification in `1–3` engineering days. If a story takes more than 3 days, split it vertically by workflow milestone (*Create Draft -> Submit -> Approve/Reject*) or risk slice (*Happy Path + Core Validation -> Concurrency/Bulk Edge Cases*), never horizontally by layer.
2. **Unbroken End-to-End Traceability Chain**: Maintain permanent, never-recycled IDs across every downstream skill:
   `EPIC-ID -> FR-ID -> US/JOB-ID -> FLOW-ID -> SCR/STATE-ID -> AC-ID -> TASK-ID -> TEST-ID -> METRIC-ID`.
3. **User Story vs Job Story Selection**:
   - Use **User Stories** (`As a <role>, I want <capability>, so that <measurable outcome>`) when RBAC/ABAC roles and tenant boundaries drive system behavior.
   - Use **Job Stories** (`When <situational trigger>, I want to <action>, so I can <outcome>`) when urgency, operational context, or failure recovery drives behavior regardless of persona label.
4. **Explicit Layer Sub-Tasks Within One Vertical Story**: Keep `[DB]`, `[API]`, `[UI]`, and `[QA]` sub-tasks grouped under the SAME story so a story is never closed until all four layers integrate cleanly.
5. **Contract-First Parallelism (Slice 0)**: When frontend and backend teams work concurrently, lock the OpenAPI 3.1 / TypeScript interface and expand-only DB schema in Slice 0 so `[API]` and `[UI]` advance in parallel without mock drift.

## 4. Architecture & Implementation
### Typed Vertical Story & Traceability Blueprint
```typescript
export type StoryStatus = 'CONFIRMED' | 'PROPOSED' | 'UNKNOWN' | 'DEFERRED';
export type TaskLayer = 'DB' | 'API' | 'UI' | 'QA' | 'OPS_GATE';

export interface VerticalTaskSpec {
  readonly taskId: string;
  readonly layer: TaskLayer;
  readonly summary: string;
  readonly estimatedHours: number;
  readonly dependsOn: readonly string[];
  readonly negativeHttpStatuses: readonly number[];
}

export interface VerticalStorySpec {
  readonly epicId: string;
  readonly storyId: string;
  readonly frRef: string;
  readonly acRefs: readonly string[];
  readonly flowRef: string;
  readonly sliceType: 'vertical';
  readonly status: StoryStatus;
  readonly estimatedDays: number;
  readonly tasks: readonly VerticalTaskSpec[];
}

export function validateVerticalStorySize(
  story: VerticalStorySpec,
): readonly string[] {
  const issues: string[] = [];
  if (story.estimatedDays > 3) {
    issues.push(
      `${story.storyId}: exceeds 3-day thin-slice cap (${story.estimatedDays}d); split by workflow milestone.`,
    );
  }
  if (story.acRefs.length === 0) {
    issues.push(`${story.storyId}: missing AC-* acceptance criteria references.`);
  }
  const hasQa = story.tasks.some((task) => task.layer === 'QA');
  if (!hasQa) {
    issues.push(`${story.storyId}: missing [QA] verification task inside vertical slice.`);
  }
  return issues;
}
```

### Example Vertical Slice Decomposition (`US-014`)
```yaml
epic_id: EPIC-02
story_id: US-014
fr_ref: FR-PO-012
flow_ref: FLOW-PO-APPROVE
ac_refs: [AC-PO-012-01, AC-PO-012-02, AC-PO-012-03, AC-PO-012-04]
slice_type: vertical
estimated_days: 2
tasks:
  - task_id: TASK-014-DB
    layer: DB
    summary: Add optimistic version integer + immutable approval_audit table (expand-only)
    depends_on: [TASK-000-CONTRACT]
  - task_id: TASK-014-API
    layer: API
    summary: POST /api/v1/purchase-orders/:id/approve enforcing maker-checker 403 & ETag 409
    depends_on: [TASK-014-DB]
    negative_http_statuses: [400, 401, 403, 404, 409, 422]
  - task_id: TASK-014-UI
    layer: UI
    summary: Approve/Reject modal binding 9-state contract (409 conflict diff, 403 denied, 375px mobile)
    depends_on: [TASK-000-CONTRACT]
  - task_id: TASK-014-QA
    layer: QA
    summary: Unit + DB integration tests (200/403/409/422) + Playwright mobile overflow check
    depends_on: [TASK-014-API, TASK-014-UI]
```

## 5. Platform / Vendor Variations
- **Full-Stack Web Monolith / Modular Monolith**: Single PR or tightly paired sequential PRs deliver `[DB] -> [API] -> [UI] -> [QA]` within 1–2 days against one local ephemeral test DB.
- **Mobile + Backend Dual-Repo Teams**: Split Slice 0 into versioned API contract + backward-compatible additive fields (`/shadow-compat`) so mobile client upgrades survive skewed deployments safely (`/shadow-mobile`).
- **Regulated Enterprise / Government Backlogs**: Embed explicit `KAK-Clause` or `FR-ID` cross-reference tags on every Jira/GitHub/Abhiwork issue so monthly progress reports (`/shadow-doc`) and Staging RTM (`/shadow-uat`) reconcile automatically.

## 6. Decision Matrix & Trade-Offs
| Slicing Pattern | When to Use | Risk if Misused | Verdict |
| :--- | :--- | :--- | :--- |
| **Workflow-Milestone Vertical Slice** (*Draft -> Submit -> Approve*) | Multi-step business processes with approvals or payments | Slightly more upfront contract alignment | **Recommended Default** |
| **Data-Variant Vertical Slice** (*Single-item -> Bulk CSV*) | Complex imports, batch payouts, or reporting exports | Temptation to skip pagination/async `HTTP 202` until late | Strong for high-volume modules |
| **Contract-First Slice 0 + Parallel `[API]`/`[UI]`** | Separate frontend & backend developers | Mock schema drift if OpenAPI contract isn't validated in CI | Pair with contract tests (`/shadow-test`) |
| **Horizontal Layer Slicing** (*All DB -> All API -> All UI*) | Almost never (only trivial 1-table migration spikes) | Integration defects, auth mismatches & UX gaps explode in final week | **Anti-Pattern — Reject** |

## 7. Real Production Scenario
**Context:** A 6-week ERP warehouse project initially planned Sprint 1 for *"Build all 28 PostgreSQL tables"*, Sprint 2 for *"Build all 45 REST endpoints"*, and Sprint 3 for *"Connect React screens"*.
**Failure:** In Week 5, when the UI finally connected to the Stock Transfer endpoint, engineers discovered the DB schema lacked partial-shipment statuses and the API ignored `tenant_id` scoping on search filters—forcing 11 days of cascading schema, API, and frontend rework right before UAT.
**Fix:** Re-slicing remaining modules into 2-day vertical slices (`Receive Stock`, `Transfer Stock`, `Stock Opname Adjustment`), each integrating DB + API + UI + negative integration tests before closure, surfaced contract mismatches on Day 2 instead of Week 5.

## 8. Failure Modes & Edge Cases
- **WRONG (Horizontal Mega-Stories):** Creating `US-01: Create all database tables for Billing` and `US-02: Create all Billing frontend pages`, each spanning 10+ days with zero runnable user capability at sprint end.
  **RIGHT:** Slice vertically into `US-01: Create & View Draft Invoice (DB+API+UI+Tests, 2d)`, `US-02: Issue Invoice with Numbering & PDF (2d)`, and `US-03: Record Partial Payment & Reconciliation (3d)`.
- **WRONG (Orphan Technical Tasks Missing Traceability):** Logging `"Refactor auth middleware"` or `"Build dashboard widget"` with no `FR-*` or `AC-*` link.
  **RIGHT:** Bind every feature task to its `FR-*`, `US-*`, and `AC-*` IDs; tag genuine technical enablers cleanly as `TECH-ENABLER` linked to the specific `NFR-*` or `EPIC-*` they unblock.

## 9. Testing & Verification
- Run `python shadow-plan/scripts/sprint_dag_verifier.py --check-plan <plan.json>` to automatically detect missing `FR-*`/`US-*`/`AC-*` traceability links and horizontal-layer anti-pattern flags (`PLAN_MISSING_TRACEABILITY`, `PLAN_HORIZONTAL_LAYER_SMELL`).
- Inspect every story's `[QA]` task to verify explicit negative HTTP statuses (`400`, `401`, `403`, `404`, `409`, `422`) rather than generic *"write unit tests"*.

## 10. Operational Considerations
- Keep active Work-In-Progress (WIP) capped per developer (`<= 2` concurrent stories) so slices reach `Done` completely before new slices start.
- Never silently mutate scope mid-sprint when a client introduces an out-of-contract feature; log it and escalate to `/shadow-pmo` for Defect vs Paid CR classification.

## 11. Authoritative References
- **Mike Cohn** — *User Stories Applied* & *SPIDR Story Splitting* (Spikes, Paths, Interfaces, Data, Rules).
- **Shadow Design Handoff Pack** — [`10-handoff-and-measurement.md`](../../shadow-design/references/ai-product-designer-skill-pack/10-handoff-and-measurement.md) & `pm-execution/skills/user-stories/SKILL.md`.
- **ISO/IEC/IEEE 12207:2017** — *Software life cycle processes (Implementation & Traceability)*.

## 12. Limitations & When NOT to Use
- **Do NOT use** for contractual PERT/Monte Carlo P80 schedule forecasting, Earned Value Management (`CPI`/`SPI`), or Paid Change Request commercial evaluation — route to `/shadow-pmo`.
- **Do NOT use** for unvalidated requirements where actors or business rules are still contradictory — return to `/shadow-discovery` first.
