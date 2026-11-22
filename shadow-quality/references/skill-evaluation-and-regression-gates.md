# Skill Evaluation, Regression Gates & Ownership Verification (`W0`)

## 1. Purpose & Activation Conditions
Enforce evidence-based quality gates across Shadow Army skills and application codebases: deterministic baseline vs post-change regression scoring, `evaluations.md` scenario validation, cross-skill ownership verification, and honest `NOT_RUN` reporting. Load when reviewing skill upgrades, designing quality gates, or auditing baseline regressions.

## 2. Prerequisites
- Familiarity with `shadow-quality/scripts/shadow_gate.py`, `evals/validate_skill_evaluations.py`, and `shadow-monarch/reference/CROSS-SKILL-OWNERSHIP-MATRIX.md`.

## 3. Technical Principles & Constraints
- **Evidence Over LOC:** Never judge skill or code quality by file count or Markdown lines. Grade strictly on verified competency: problem framing, security invariants, implementation fit, failure/recovery coverage, and reproducible verification.
- **Unified Status Taxonomy (`PASS | FAIL | NOT_RUN | BLOCKED | NOT_APPLICABLE`):** Never claim `PASS` without actual command output executed AFTER the final edit. Any live external, production, or API-cost evaluation not executed MUST be declared `NOT_RUN` explicitly.
- **No Benchmark Theater:** Aggregate scores MUST NOT mask a single safety-critical failure (`0` unapproved external mutations, `0` cross-tenant/IDOR bypasses, `0` secret/PII leaks). Report failure rates per category.
- **Minimal Change & Ownership Integrity:** Reject unsolicited directory migrations, competing specs, or changes outside the authorized wave/task scope.

## 4. Architecture & Implementation
```powershell
# Unified offline W0 quality & skill-evaluation verification chain (L0/L1)
python "evals/validate_skill_evaluations.py" --summary-only
python "shadow-monarch/scripts/skill_router.py" --audit-descriptions
python "shadow-monarch/scripts/skill_router.py" --self-test
python "shadow-quality/scripts/shadow_gate.py" --repo . --probes-verified
python -m unittest evals/test_repo_coverage_integrity.py evals/test_validate_skill_evaluations.py -v
```
Baseline vs Post-Change Comparison Schema:
```typescript
export type GateStatus = 'PASS' | 'FAIL' | 'NOT_RUN' | 'BLOCKED' | 'NOT_APPLICABLE';

export interface WaveRegressionSnapshot {
  readonly waveId: string;
  readonly skill: string;
  readonly baselineRouterProbesPassed: number;
  readonly postChangeRouterProbesPassed: number;
  readonly evaluationScenariosCount: number;
  readonly safetyGateStatus: GateStatus;
  readonly unitTestsStatus: GateStatus;
  readonly liveLlmEvalStatus: GateStatus; // Explicitly 'NOT_RUN' unless L3 approved
  readonly unresolvedRisks: readonly string[];
}
```

## 5. Platform / Vendor Variations
| Gate Layer | Tooling in Repository | Scope & Side-Effect Boundary |
| :--- | :--- | :--- |
| **Repo Integrity & Link Gate** | `evals/test_repo_coverage_integrity.py` | `L0` read-only — verifies all 59 skills routed, documented, portable |
| **Skill Eval & Ref-Guide Gate** | `evals/validate_skill_evaluations.py` | `L0` read-only — checks `## Reference Guide` index & `evaluations.md` guards |
| **Code & Drift Gate** | `shadow-quality/scripts/shadow_gate.py` | `L0`/`L1` — strict TS (`0 any`/`0 cast`/`0 !`), secrets, brownfield drift, Docker ownership |
| **Cross-Model Agent Eval** | `evals/run_evals.py --agent` | **`L3_RESOURCE_INTENSIVE`** — requires explicit Monarch approval & token budget |

## 6. Decision Matrix & Trade-Offs
| Verification Signal | Safe Default? | Blocks Merge/Release? | When to Require |
| :--- | :---: | :---: | :--- |
| **Static Typecheck + Lint + `shadow_gate.py`** | Yes (`L1`) | YES | Every code or skill PR |
| **Router Positive + Negative Confusion Probes** | Yes (`L0`) | YES | Every skill description/trigger change |
| **Offline Verifier CLI + Unit Tests** | Yes (`L1`) | YES | Every skill carrying a verifier script |
| **Live Multi-Model LLM Eval Sweep** | No (`L3`) | Only on major model/prompt releases | Explicit Monarch approval with cost cap |

## 7. Real Production Scenario
A skill upgrade expands reference documentation by 1,200 lines and achieves 100% pass on 3 happy-path prompts, yet subtly introduces a regex trigger collision that steals `shadow-auth` prompts into `shadow-sec` and drops `shadow-cache` test coverage to 0. Running `skill_router.py --self-test` + `validate_skill_evaluations.py` catches both the ownership conflict and missing negative guards offline in `< 2 seconds` before merge.

## 8. Failure Modes & Edge Cases
- **WRONG:** Reporting `"96% evals passed — ready to merge!"` while hiding 1 failed cross-tenant authorization scenario inside the aggregate percentage.
- **RIGHT:** Enforce `100%` pass on all safety-critical scenarios as an independent non-compensatory gate and report per-category breakdowns.
- **WRONG:** Running `git push` or `evals/run_evals.py --agent` automatically during a `code_review` or offline wave check.
- **RIGHT:** Keep reviews strictly `L0_READ_ONLY`, offline gates `L1`, and request explicit Monarch approval for `L3`/`L4`.

## 9. Testing & Verification
- Execute `python -m unittest evals/test_validate_skill_evaluations.py -v` and `python shadow-quality/scripts/shadow_gate.py --repo . --probes-verified` after any change to `shadow-quality` or `evals/`.

## 10. Operational Considerations
- Track wave-over-wave trends (`skills_missing_ref_guide_count`, `skills_with_evaluations_md`, `total_router_probes`, `unit_test_dirs`) in every wave handoff report so progress stays verifiable and reversible.

## 11. Authoritative References
- ISO/IEC 25010:2023 — *Systems and software Quality Requirements and Evaluation (SQuaRE)* (`https://www.iso.org/standard/78176.html`).
- Shadow Monarch Cross-Skill Ownership Matrix (`shadow-monarch/reference/CROSS-SKILL-OWNERSHIP-MATRIX.md`).

## 12. Limitations & When NOT to Use
- Deterministic offline validators prove structural integrity, zero syntax/type drift, and routing precision, NOT live LLM reasoning accuracy across unseen user phrasing; pair with explicit `NOT_RUN` disclosures until `L3` live evals are authorized.
