# Phase 5 — Routing & Overhead Measurement Report (`SA-SE-ENH-001`)

## 1. Before vs After Quantitative Measurements
Only directly measured artifacts are listed below (live external LLM token-consumption telemetry is marked `NOT_RUN`):

| Metric | Baseline (`185c42a`) | Enhanced (`SA-SE-ENH-001`) | Delta | Status |
|---|---:|---:|---|---|
| Total Registered Skills | `45` | `52` | `+7` | `PASS` |
| Frontmatter `Use when...` & <=500 chars Audit | `45/45` | `52/52` | `+7` | `PASS` |
| `skill_router.py --self-test` Probes | `17/17` | `32/32` | `+15` probes | `PASS` |
| `shadow-monarch/SKILL.md` Size | `313` lines / `36,553` bytes | `318` lines / `40,508` bytes | `+5` lines / `+3,955` bytes | `PASS` |
| `shadow-monarch/GLOBAL.md` Size | `83` lines / `13,799` bytes | `83` lines / `14,221` bytes | `0` lines / `+422` bytes | `PASS` |
| Trivial / Typo-Only Edit Loaded Skills | `0` companions / `0` refs | `0` companions / `0` refs / `0` antislop | `§5.3` typo-only exclusion enforced | `PASS` |

## 2. Router Decision Record (`§2.2`) & 3-Layer Progressive Loading (`§2.1`)
`python "shadow-monarch/scripts/skill_router.py" --route "<prompt>"` emits both backward-compatible keys and the full `routing_decision` contract (`task_id`, `intent`, `primary_skill`, `supporting_skills`, `risk_review_skills`, `activation_reason`, `excluded_skills`, `required_permissions`, `prohibited_actions`).

### Observed Sample 1 (`§5.1` Row 1)
- **Prompt:** `"Our checkout API returns 500 randomly under concurrency with misleading stack trace."`
- **Result:** `primary_skill: "shadow-debug"`, `supporting_skills: ["shadow-test"]`, `risk_review_skills: ["shadow-observe"]`, `always_on_ui_skills: []`.

### Observed Sample 2 (`§5.3` Negative Trigger 1)
- **Prompt:** `"Typo-only README edit: fix spelling of installation."`
- **Result:** `primary_skill: "shadow-monarch"`, `supporting_skills: []`, `risk_review_skills: []`, `always_on_ui_skills: []`, `reference_modules: []`, `excluded_skills: [{"skill": "shadow-architect/shadow-sec/shadow-browser", "reason": "Negative trigger §5.3: typo-only README edit uses Layer 1 minimal safeguards."}]`.

## 3. Probe Matrix Summary (`32/32` PASS)
- `AUDIT-1`: `52/52` `SKILL.md` files pass trigger and `<= 500`-char checks.
- `RECALL-1`..`RECALL-14`: All `14` legacy domain/consulting probes pass without slash commands (initial `RECALL-14` primary selection issue resolved by preserving specificity order in `matched_ordered`).
- `S51-1`..`S51-10`: All `10` ownership rows in `§5.1` pass (initial plural regex gap on `shadow-domain` resolved by supporting `approvals?`, `cancellations?`, `contexts?`).
- `NEG-1`..`NEG-5` & `PRECISION-1`..`PRECISION-2`: All `7` negative-trigger and anti-leakage probes pass (`shadow-perf` excluded during UI coding, `shadow-ops` excluded on queue-semantics design, `shadow-supplychain` excluded on tender pricing, and unauthorized prod-DB request flags missing approval).
