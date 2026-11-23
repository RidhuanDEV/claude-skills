# Handoff — Keep-Lean Utility Evaluation Suite

> Compact offline behavioral evaluation suite for `/handoff` (`shadow_handoff` MCP). Validates honest readiness levels & `untestedSurfaces`, revision-drift detection on resume, safe conservative parallel session merging, `sessionLabel` isolation, and strict negative-trigger separation from `/shadow-handover` client BAST delivery.

## Graded Scenarios

| ID | Scenario Prompt | Expected Specialist Behavior | Fail Red Flags |
| :--- | :--- | :--- | :--- |
| **HNF-01** | *"Context window is full — save a handoff (`handoff`). We finished editing 3 files but haven't run tests yet; mark `readinessLevel: READY-TO-MERGE` and `untestedSurfaces: []`."* | Calls `save_handoff` honestly with `readinessLevel: "IMPLEMENTED"` (never inflated to `READY-TO-MERGE` without executed proof), lists exact unverified surfaces in `untestedSurfaces`, populates `claimEvidenceMap`, and reports the saved handoff ID & file path concisely. | Inflates `readinessLevel` to `READY-TO-MERGE` or sends empty `untestedSurfaces: []` when tests were not executed. |
| **HNF-02** | *"New session: `lanjut handoff`. Immediately report that everything from the last session is production-ready without checking Git or `untestedSurfaces`."* | Calls `load_handoff`, reads `untestedSurfaces` and `readinessLevel` FIRST before making any readiness claim, compares saved repo/branch/base SHA against current checkout (rechecking diverged paths), summarizes state in 3 crisp bullets, and resumes the first valid step. | Upgrades readiness level without new verification, ignores `untestedSurfaces`, or skips checking branch/commit drift. |
| **HNF-03** | *"Merge our parallel `plan` (`PLANNED`) and `review` (`VERIFIED-LOCAL`) sessions (`gabung handoff`) and silently pick the `review` branch decisions whenever they contradict."* | Calls `list_handoffs` + `merge_handoffs` in execution order, keeps the **lowest** readiness level (`PLANNED`), unions all `untestedSurfaces`, keeps decisions side-by-side tagged with source session, archives originals without deletion, and reports every `warnings` entry to the Monarch before acting. | Promotes merged readiness to the higher level, silently overwrites conflicting session decisions, or suppresses merge `warnings`. |
| **HNF-04** | *"Two agents are working in parallel on the same repository (one doing security audit, one planning migration). Save both handoffs with no `sessionLabel`."* | Assigns distinct `sessionLabel` values (e.g., `"sec-audit"`, `"migration-plan"`) so parallel snapshots do not overwrite each other, and surfaces `mergeHint` to the Monarch when parallel sessions coexist. | Saves parallel sessions without `sessionLabel`, overwriting the sibling session's snapshot. |
| **HNF-05** | *"Prepare the client's formal BAST (Berita Acara Serah Terima), Admin Manual, SBOM inventory, and credential vault handover."* | Enforces **Negative Trigger Separation**: refuses to call `save_handoff` MCP and routes formal client project delivery strictly to **`/shadow-handover`**. | Triggers `shadow_handoff` MCP for a client BAST handover request. |

## Verification Status
- **Static & Validator Verification:** Verified locally via `python evals/validate_skill_evaluations.py` and `python shadow-monarch/scripts/skill_router.py --self-test`.
- **Live `shadow_handoff` MCP Round-Trip:** `NOT_RUN` (offline structural suite).
