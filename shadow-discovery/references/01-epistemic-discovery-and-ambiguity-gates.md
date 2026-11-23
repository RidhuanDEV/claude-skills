# 01. Epistemic Discovery, Strategy Framing & Ambiguity Stop Gates

## 1. Purpose & Activation Conditions
Use this playbook at the start of SDLC Stage 1 (`/shadow-discovery`) whenever raw stakeholder briefs, client RFPs, interview notes, or feature ideas arrive with implicit assumptions, missing actor permissions, or contradictory rules. Its objective is to turn ambiguous desires into an auditable, evidence-tagged discovery baseline before any architecture (`/shadow-architect`) or code changes begin.

Activate this playbook when:
- A brief relies on vague quality adjectives (*"fast"*, *"secure"*, *"easy"*, *"auto-approve"*) or omits who can create, approve, cancel, or audit a workflow.
- Existing codebase behavior and stakeholder requests appear to conflict.
- A requirement touches money, legal compliance, access control, SLA clocks, or destructive state transitions and leaves edge cases unstated.

## 2. Prerequisites
- Access to existing repository artifacts when brownfield (`README`, API routes, database schema, OpenAPI specs, existing tickets, or analytics snapshots) so current behavior is verified as `[EVIDENCE]`.
- Stakeholder brief, TOR/KAK excerpt, or feature request text.
- Companion routing awareness: [`shadow-design/references/ai-product-designer-skill-pack/01-discovery-and-evidence.md`](../../shadow-design/references/ai-product-designer-skill-pack/01-discovery-and-evidence.md) for JTBD framing; `/shadow-presales` if commercial KAK pricing/RAB is requested; `/shadow-pmo` if the request alters a signed fixed-price contract.

## 3. Technical Principles & Constraints
1. **Mandatory 4-Tag Epistemic Discipline**: Every claim in a discovery document MUST carry exactly one provenance tag:
   - `[EVIDENCE]`: Directly observed in repo code, database constraints, production logs, dated user interviews, or signed source documents.
   - `[ASSUMPTION]`: Working hypothesis not yet verified; MUST state **risk if wrong** and **validation method**.
   - `[PROPOSAL]`: Recommended design or policy choice awaiting stakeholder sign-off.
   - `[NEEDS VALIDATION]`: Blocking ambiguity that cannot be resolved safely from current context.
2. **Zero Fabricated Research**: Never invent stakeholder quotes, user personas, interview counts, or market statistics. If research has not been conducted, declare `NOT TESTED / NO PRIMARY INTERVIEWS` explicitly.
3. **The Ambiguity Stop Gate**: Never silently guess rules governing financial calculations, tax/rounding, RBAC/ABAC authorization, tenant boundaries, retention/deletion legality (UU PDP), or SLA business-day calendars. Ask **one focused clarifying question** with concrete options and a recommended default before locking downstream design.
4. **Five Foundational Strategy Questions**: Before writing detailed functional specs, validate: (1) *Problem Validation* (recurring measurable pain?), (2) *Audience Definition* (which actor + tenant scope?), (3) *Solution Fit* (root cause vs symptom?), (4) *Smallest Testable Slice (MVP)*, and (5) *Existing System Landscape* (how is it handled today?).
5. **Single-Question Economy**: Batch unrelated nitpicks out of blocking questions; if only one blocking decision gates the spec, ask that single concise question cleanly rather than overwhelming stakeholders with a 20-question survey.

## 4. Architecture & Implementation
Model discovery claims, actors, scope boundaries, and blocking ambiguity gates using explicit typed contracts so discovery artifacts feed cleanly into `/shadow-doc` Canonical JSON AST v2.0 and automated completeness audits:

```typescript
export type EpistemicTag =
  | 'EVIDENCE'
  | 'ASSUMPTION'
  | 'PROPOSAL'
  | 'NEEDS_VALIDATION';

export type ImpactDomain =
  | 'MONEY'
  | 'AUTHZ'
  | 'LEGAL_PRIVACY'
  | 'DESTRUCTIVE_STATE'
  | 'SLA_CALENDAR'
  | 'UX_COPY';

export interface DiscoveryClaim {
  readonly id: string;
  readonly statement: string;
  readonly tag: EpistemicTag;
  readonly domain: ImpactDomain;
  readonly sourceRef: string | null;
  readonly riskIfWrong: string | null;
  readonly validationPlan: string | null;
}

export interface ClarificationQuestion {
  readonly claimId: string;
  readonly question: string;
  readonly options: readonly string[];
  readonly recommendedDefault: string;
}

const BLOCKING_DOMAINS: ReadonlySet<ImpactDomain> = new Set([
  'MONEY',
  'AUTHZ',
  'LEGAL_PRIVACY',
  'DESTRUCTIVE_STATE',
  'SLA_CALENDAR',
]);

export function evaluateAmbiguityStopGate(
  claims: readonly DiscoveryClaim[],
): { readonly blocked: boolean; readonly blockingIds: readonly string[] } {
  const blockingIds: string[] = [];

  for (const claim of claims) {
    if (claim.tag === 'EVIDENCE' && claim.sourceRef === null) {
      blockingIds.push(`${claim.id}:MISSING_EVIDENCE_SOURCE`);
    }
    if (
      claim.tag === 'NEEDS_VALIDATION' &&
      BLOCKING_DOMAINS.has(claim.domain)
    ) {
      blockingIds.push(claim.id);
    }
    if (
      claim.tag === 'ASSUMPTION' &&
      (claim.riskIfWrong === null || claim.validationPlan === null)
    ) {
      blockingIds.push(`${claim.id}:UNTRACKED_ASSUMPTION_RISK`);
    }
  }

  return {
    blocked: blockingIds.length > 0,
    blockingIds,
  };
}
```

### Mandatory Stakeholder & Actor Scope Matrix Template
| Actor / Role | Tenant & Data Scope | Permitted Actions | Explicit Prohibitions (Negative AuthZ) | Evidence Source |
| :--- | :--- | :--- | :--- | :--- |
| `Requester` | Own `tenant_id`, own drafts | Create, edit draft, submit, cancel before approval | Cannot self-approve or view other tenants | `[EVIDENCE: auth/rbac.ts]` |
| `Approver` | Own `tenant_id`, assigned cost center | Approve, reject with mandatory reason | Cannot approve own submitted records (maker-checker) | `[EVIDENCE: KAK §4.2]` |
| `Auditor` | Read-only across assigned scope | View audit log, export masked reports | Zero write/delete mutations; no unmasked Specific PII | `[PROPOSAL: UU PDP Ps. 4]` |

## 5. Platform / Vendor Variations
- **Greenfield SaaS / Product Discovery**: Start with Opportunity Solution Trees (`pm-product-discovery`), problem validation, and MVP In-Scope vs Out-of-Scope slicing; expect higher `[ASSUMPTION]` density requiring rapid prototype or experiment validation.
- **Brownfield Enterprise / Legacy Modernization**: Inspect codebase routes, database constraints, migrations, and production error logs FIRST so `[EVIDENCE]` captures undocumented legacy invariants (e.g., soft-delete rules, implicit batch cutoffs) before accepting stakeholder memory at face value.
- **Government / Regulated Procurement (TOR/KAK — Indonesia)**: Anchor every requirement to exact clause numbers (`KAK Bab III.2`, `Perpres`, `UU PDP No. 27/2022`). Separate technical requirement elicitation (`/shadow-discovery`) strictly from tender pricing/BoQ (`/shadow-presales`) and contractual CR impact (`/shadow-pmo`).

## 6. Decision Matrix & Trade-Offs
| Discovery Situation | Required Action | Trade-Off & Rationale | Exit Condition |
| :--- | :--- | :--- | :--- |
| Ambiguous auth, billing, tax, or SLA calendar rule | **Stop & Ask 1 Focused Question** with concrete options + recommended default | Minor upfront pause prevents `10x` rework and security/legal bugs post-build | Stakeholder selects option; tag flips to `[EVIDENCE]` |
| Non-critical UI wording or default sort order | **Record `[PROPOSAL]` with Recommended Default** and continue | Preserves momentum without polling stakeholders on routine UX defaults | Confirmed during async PRD review |
| Stakeholder brief contradicts existing DB schema | **Flag Contradiction Explicitly** (`[EVIDENCE]` vs `[NEEDS VALIDATION]`) | Surfaces hidden migration cost before sprint commitment | Explicit decision: adapt rule or schedule migration |
| Request adds features outside signed contract/SOW | **Log in Out-of-Scope Ledger & Route to `/shadow-pmo`** | Protects MVP schedule and prevents uncompensated scope creep | Written exclusion or formal Paid CR approval |

## 7. Real Production Scenario
**Context:** A B2B logistics company requested an *"automated invoice auto-cancel feature after 3 days if unpaid"*. A rushed draft PRD assumed 72 UTC hours and hard-deleted unpaid records.
**Discovery Audit:** Inspecting the existing billing schema (`[EVIDENCE: migrations/014_invoices.sql]`) revealed `Asia/Jakarta` settlement cutoffs, bank transfer reconciliation delays on Indonesian national holidays (`SKB Bersama`), and an accounting regulation forbidding hard deletes of issued invoice numbers.
**Resolution:** The analyst tagged the SLA unit as `[NEEDS VALIDATION]` and asked one focused question: *"Should the 3-day unpaid cancellation clock count (A) 3 Indonesian business days ending 17:00 WIB excluding SKB Bersama holidays (Recommended), or (B) 72 calendar hours from issuance, transitioning status to `EXPIRED` (never hard-deleted)?"* The finance lead selected Option A within 10 minutes, preventing an accounting audit violation and weekend false cancellations.

## 8. Failure Modes & Edge Cases
- **WRONG (Silently inventing critical policy defaults):** Seeing *"auto-cancel after 3 days"* and hardcoding `NOW() + INTERVAL '72 hours'` in UTC with `DELETE FROM invoices` without asking about timezone, weekends, or audit retention.
  **RIGHT:** Tag the policy `[NEEDS VALIDATION]`, state the accounting/timezone risk, and ask one crisp question offering concrete business-day vs calendar-hour options while preserving immutable audit status transitions.
- **WRONG (Persona fiction presented as research):** Writing *"Based on interviews with 12 enterprise managers, users hate multi-step modals"* when zero interviews were conducted.
  **RIGHT:** Label the claim `[ASSUMPTION]` with risk-if-wrong and a lightweight validation plan (e.g., 5 task-usability sessions via `shadow-design`'s `interview-script`).
- **WRONG (Conflating Discovery with Pricing or CR Approval):** Estimating tender RAB prices inside a product PRD or absorbing an unapproved Change Request silently into an active sprint.
  **RIGHT:** Keep `/shadow-discovery` focused on requirements clarity; route KAK pricing/sizing to `/shadow-presales` and contractual scope changes to `/shadow-pmo`.

## 9. Testing & Verification
- **Automated Ambiguity Regression Check**: Run `python -m unittest discover -s shadow-discovery/tests -v` to confirm single-question ambiguity gating behaves deterministically (`test_ambiguity_single_question.py`).
- **Red-Team Contradiction Walkthrough**: Cross-check every actor row in the Stakeholder Matrix against every Functional Requirement to verify zero conflicting permissions (e.g., `FR-004` allowing CSV export of raw NIK while `NFR-003` bans bulk unmasked Specific PII export).
- **Evidence Provenance Audit**: Verify `100%` of `[EVIDENCE]` tags cite an inspectable file path, ticket ID, or dated stakeholder sign-off; `0` unresolved `[NEEDS VALIDATION]` tags remain in `BLOCKING_DOMAINS` at Stage 1 Exit.

## 10. Operational Considerations
- Maintain an immutable **In-Scope vs Out-of-Scope Ledger** at the top of every PRD/SRS so downstream `/shadow-plan`, `/shadow-uat`, and `/shadow-pmo` agents share one authoritative boundary.
- Assign permanent, never-renumbered IDs (`FR-MOD-001`, `NFR-001`, `ASM-001`) from Day 1; deprecate obsolete IDs with status `DEPRECATED` rather than recycling numbers.
- Version discovery changes cleanly inside `/shadow-doc` Canonical JSON AST v2.0 whenever formal stakeholder sign-off is required.

## 11. Authoritative References
- **ISO/IEC/IEEE 29148:2018** — *Systems and software engineering — Life cycle processes — Requirements engineering* (criteria for unambiguous, verifiable, consistent requirements).
- **BABOK Guide v3 (IIBA)** — *Elicitation and Collaboration; Requirements Life Cycle Management*.
- **Shadow Design Discovery Pack** — [`01-discovery-and-evidence.md`](../../shadow-design/references/ai-product-designer-skill-pack/01-discovery-and-evidence.md) & `ghaida-intent/skills/strategize/SKILL.md`.

## 12. Limitations & When NOT to Use
- **Do NOT use** for tender commercial pricing, HPS/RAB BoQ modeling, or 3-scenario infrastructure sizing — route to `/shadow-presales`.
- **Do NOT use** for contractual Paid Change Request disputes, PERT/Monte Carlo schedules, or Earned Value Management — route to `/shadow-pmo`.
- **Do NOT use** for trivial 1-line bug fixes where the failing behavior and expected contract are already verified in existing tests — route directly to `/shadow-debug`.
