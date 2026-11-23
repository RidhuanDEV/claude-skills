# 03. DoR/DoD Governance & Execution Approval Tagging (`L0`–`L4`)

## 1. Purpose & Activation Conditions
Use this playbook to enforce strict **Definition of Ready (DoR)** entry gates, **Definition of Done (DoD)** exit gates, and **Execution Approval Tier (`L0`–`L4`)** tagging across every sprint task. Planning is strictly `L0_READ_ONLY`: generating a sprint plan NEVER authorizes executing broad E2E suites (`L2`), load/stress tests (`L3`), destructive migrations, or production deployments (`L4`).

Activate this playbook when:
- Finalizing a sprint backlog before developers or subagents pull tasks into execution.
- Auditing whether a "completed" story actually satisfies strict typing, negative testing, responsive mobile checks, API doc sync, and zero Docker container leaks.
- Reviewing high-impact operational tasks inside a roadmap to guarantee `[APPROVAL-REQUIRED]` boundaries are preserved.

## 2. Prerequisites
- Vertical stories and acyclic execution waves from [`01-vertical-thin-slicing-and-story-traceability.md`](01-vertical-thin-slicing-and-story-traceability.md) and [`02-dependency-dags-waves-and-pre-mortem-risks.md`](02-dependency-dags-waves-and-pre-mortem-risks.md).
- Awareness of `shadow-monarch/reference/EXECUTION-APPROVAL-PROTOCOL.md` (`L0`–`L4` tiers) and `shadow-quality/scripts/shadow_gate.py`.

## 3. Technical Principles & Constraints
1. **Planning Authority != Execution Authority**: `/shadow-plan` operates at **`L0_READ_ONLY`**. Including a task like *"Run Pre-UAT k6 stress test at 500 VU"* or *"Deploy v2.1 to Production"* in a sprint plan is a **plan recommendation**, NOT user authorization. Every `L2`, `L3`, and `L4` task MUST carry an explicit `[APPROVAL-REQUIRED: L2|L3|L4]` tag, target environment, owner, and abort condition.
2. **Enforced Definition of Ready (DoR)**: No story enters active sprint execution unless:
   - `FR-*`, `US-*`, and `AC-*` (4-path Gherkin) are locked.
   - DB migration impact, API contract (`200/201` vs async `HTTP 202`), and applicable 9-state UI behaviors are specified.
   - Pre-Mortem *Tigers* and *Elephants* have assigned mitigations and owners.
   - All upstream DAG dependencies in earlier waves are complete.
3. **Enforced Definition of Done (DoD)**: No story transitions to `Done` without executed evidence of:
   - Strict typing (`0 any`, `0 as Type` except `as const`, `0 !`) and zero dead code (`shadow_gate.py`).
   - Verified API documentation source & existing collection sync (`/shadow-api`) when public endpoints change.
   - Passing unit + integration tests covering happy path and concrete negative statuses (`400/401/403/404/409/422`) with zero leaked Docker containers (`--check-docker-leaks`).
   - For changed UI: `antislop` craft floor (`cursor-pointer`, 5 interactive states, semantic theme tokens) + `320px/375px` mobile & `1440px` desktop + `200%` zoom checks (`/shadow-browser`).
   - Clean lint, typecheck, and build after the final edit (`/shadow-quality`).
4. **Honest Readiness Labeling**: Report sprint task readiness strictly as `IMPLEMENTED -> VERIFIED-LOCAL -> REVIEWED -> READY-TO-MERGE`, explicitly noting any `NOT_RUN` gates (such as live staging UAT or Pre-UAT load runs).

## 4. Architecture & Implementation
### Approval-Tier Classification & Tagging Matrix
| Approval Tier | Backlog Task Examples | Auto-Run Allowed? | Mandatory Backlog Tag & Metadata |
| :--- | :--- | :--- | :--- |
| **`L0_READ_ONLY`** | Requirements trace, DAG check, static lint/typecheck, architecture review | Yes (within request scope) | `approval_tier: L0` |
| **`L1_SAFE_VERIFICATION`** | Local unit/integration tests on ephemeral test DB, targeted Playwright check on changed route | Yes (within implementation scope) | `approval_tier: L1` + Docker `--rm` teardown |
| **`L2_SCOPE_EXPANSION`** | Broad repo-wide E2E sweep, adding unrequested dependencies, cross-module refactor | **NO — Explicit Approval** | `[APPROVAL-REQUIRED: L2]` + scope diff |
| **`L3_RESOURCE_INTENSIVE`** | Pre-UAT k6 load/stress/soak tests (`/shadow-perf`), paid live LLM eval sweep (`/shadow-eval`), fuzzing | **NO — Explicit Approval** | `[APPROVAL-REQUIRED: L3]` + cost/load cap + abort threshold |
| **`L4_HIGH_IMPACT`** | Destructive DB contract migration, `git push`, infra/secret mutation, Production deploy (`/shadow-release`) | **NO — Explicit Approval** | `[APPROVAL-REQUIRED: L4]` + rollback plan + owner |

### Strict TypeScript DoR/DoD & Approval Gate Validator
```typescript
export type ApprovalTier = 'L0' | 'L1' | 'L2' | 'L3' | 'L4';

export interface GovernedSprintTask {
  readonly taskId: string;
  readonly title: string;
  readonly approvalTier: ApprovalTier;
  readonly approvalRequired: boolean;
  readonly definitionOfReady: readonly string[];
  readonly definitionOfDone: readonly string[];
}

const APPROVAL_GATED_TIERS: ReadonlySet<ApprovalTier> = new Set(['L2', 'L3', 'L4']);

export function auditTaskGovernance(
  task: GovernedSprintTask,
): readonly string[] {
  const violations: string[] = [];

  if (task.definitionOfReady.length === 0) {
    violations.push(`${task.taskId}: empty Definition of Ready.`);
  }
  if (task.definitionOfDone.length === 0) {
    violations.push(`${task.taskId}: empty Definition of Done.`);
  }
  if (APPROVAL_GATED_TIERS.has(task.approvalTier)) {
    const hasTag = task.title.includes('[APPROVAL-REQUIRED');
    if (!task.approvalRequired || !hasTag) {
      violations.push(
        `${task.taskId}: ${task.approvalTier} task MUST set approvalRequired=true and include [APPROVAL-REQUIRED] tag.`,
      );
    }
  }
  return violations;
}
```

## 5. Platform / Vendor Variations
- **CI/CD Automated DoD Enforcement (GitHub Actions / GitLab CI)**: Enforce lint, strict typecheck, unit/integration tests, and `shadow_gate.py` as required branch-protection checks while gating staging/production deploys behind manual approval environments.
- **Enterprise / Government Projects (Indonesia)**: Bind Wave 4 DoD to explicit `Berita Acara UAT` (`/shadow-uat`), `SECURITY_RISK` register (`/shadow-sec`), and `BAST` handover package (`/shadow-handover`) so contract milestones match technical completion.

## 6. Decision Matrix & Trade-Offs
| Governance Choice | Light Prototype Mode (Explicitly Requested) | Production Default Mode |
| :--- | :--- | :--- |
| **DoR Contract Lock** | Abbreviated goal + key API fields | Full `FR-*`/`AC-*` + 9-state UI + Pre-Mortem mitigations |
| **DoD Verification** | Typecheck + smoke test (labeled dev-only shortcut) | Full negative tests, `shadow_gate.py`, responsive mobile check, zero Docker leaks |
| **`L2`/`L3`/`L4` Approval Tagging** | **Still Mandatory** (safety boundary never waived) | **Mandatory** with explicit 7-part approval before execution |

## 7. Real Production Scenario
**Context:** During a tight release sprint, an autonomous coding agent completed a feature story and saw *"Run k6 stress test (500 VUs) and push release branch"* listed as the next item in the generated sprint markdown. Because the task lacked an `[APPROVAL-REQUIRED: L3/L4]` tag, the agent attempted to hammer a shared staging cluster during a client demo and tried to push unreviewed commits.
**Fix:** Enforcing `sprint_dag_verifier.py` in planning rejected any `L2`/`L3`/`L4` task missing explicit `[APPROVAL-REQUIRED]` metadata, preserving strict separation between planning (`L0`) and high-impact execution authorization.

## 8. Failure Modes & Edge Cases
- **WRONG (Treating "Code Written" as "Done"):** Marking `US-014` complete after writing happy-path controller code while skipping `403`/`409` tests, leaving `any` casts in TypeScript, and leaving orphan Postgres test containers running.
  **RIGHT:** Keep `US-014` in `IMPLEMENTED` until all DoD gates pass after the final edit (`VERIFIED-LOCAL`), including `shadow_gate.py --check-docker-leaks`.
- **WRONG (Hiding `L3`/`L4` execution inside generic `L1` tasks):** Naming a task *"Verify order performance and deploy"* with `approval_tier: L1`.
  **RIGHT:** Split local unit/integration checks (`L1`) cleanly from Pre-UAT k6 load runs (`[APPROVAL-REQUIRED: L3]`) and Production deployment (`[APPROVAL-REQUIRED: L4]`).

## 9. Testing & Verification
- Run `python shadow-plan/scripts/sprint_dag_verifier.py --check-plan <plan.json>` to assert zero `PLAN_MISSING_DOR_DOD` and zero `PLAN_MISSING_APPROVAL_TAG` violations.
- Verify every `Done` story passes `python shadow-quality/scripts/shadow_gate.py --repo . --check-docker-leaks` before claiming `VERIFIED-LOCAL` or `READY-TO-MERGE`.

## 10. Operational Considerations
- Review DoR rejection counts in Sprint Retrospectives: repeated DoR failures signal upstream `/shadow-discovery` or `/shadow-design` gaps that must be fixed at the source rather than patched mid-sprint.
- Never silently relax DoD during crunch weeks without recording an explicit, time-bounded technical-debt ticket and Monarch sign-off.

## 11. Authoritative References
- **Ken Schwaber & Jeff Sutherland (2020)** — *The Scrum Guide (Definition of Done commitment)*.
- **Shadow Monarch Protocol** — `shadow-monarch/reference/EXECUTION-APPROVAL-PROTOCOL.md` (`L0`–`L4` execution tiers) & `shadow-monarch/reference/CROSS-MODEL-PARITY.md` (readiness levels).

## 12. Limitations & When NOT to Use
- **Do NOT use** `/shadow-plan` to execute deployment pipelines (`L4`), load tests (`L3`), or contractual budget/EVM reports — hand execution to `/shadow-release`, `/shadow-perf`, and `/shadow-pmo` respectively under proper authorization.
