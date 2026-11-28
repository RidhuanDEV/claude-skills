# Phase 5 — Changed Files Manifest (`SA-SE-ENH-001`)

Verified against `git status -sb` and `git diff --stat` on `<repo>` (base SHA `185c42a2fa8e520293b3819a56b681fd60b9fe18`).

## 1. Modified Tracked Files (`29` Files)
- **Orchestrator & Global Rules (`3`):**
  - `shadow-monarch/SKILL.md` (`313 -> 318` lines; `36,553 -> 40,508` bytes)
  - `shadow-monarch/GLOBAL.md` (`83 -> 83` lines; `13,799 -> 14,221` bytes)
  - `shadow-monarch/scripts/skill_router.py`
- **Deepened Existing Specialist Skills (`19`):**
  - `shadow-api/SKILL.md`
  - `shadow-architect/SKILL.md`
  - `shadow-auth/SKILL.md`
  - `shadow-cache/SKILL.md`
  - `shadow-compat/SKILL.md`
  - `shadow-data/SKILL.md`
  - `shadow-db/SKILL.md`
  - `shadow-eval/SKILL.md`
  - `shadow-git/SKILL.md`
  - `shadow-integrate/SKILL.md`
  - `shadow-maintain/SKILL.md`
  - `shadow-observe/SKILL.md`
  - `shadow-ops/SKILL.md`
  - `shadow-perf/SKILL.md`
  - `shadow-quality/SKILL.md`
  - `shadow-release/SKILL.md`
  - `shadow-resilience/SKILL.md`
  - `shadow-sec/SKILL.md`
  - `shadow-test/SKILL.md`
- **Eval Suite (`3`):**
  - `evals/README.md`
  - `evals/evals.json` (`28 -> 35` eval scenarios)
  - `evals/run_evals.py` (`EVAL_CHECKS_BY_ID` + `domain_probes` `#29`–`#35`)
- **Distribution, Packaging & Docs (`4`):**
  - `install.ps1` (`45 -> 52` skills listed in `$SkillFolders`)
  - `install.sh` (`45 -> 52` summary sync)
  - `README.md` (`52` skills & `53` reference modules breakdown)
  - `shadow-monarch.zip` (`281,496 -> 287,036` bytes)

## 2. Newly Created Specialist Skill Directories (`7` Skills / `28` Files)
1. **`shadow-debug/`**: `SKILL.md`, `methodologies/SCIENTIFIC-DEBUGGING-AND-FAULT-TREES.md`, `playbooks/DEBUG-REPORT-AND-REPRO-TEMPLATE.md`, `scripts/debug_hypothesis_gate.py`
2. **`shadow-refactor/`**: `SKILL.md`, `methodologies/CHARACTERIZATION-AND-SEMANTIC-EQUIVALENCE.md`, `playbooks/INVARIANT-LEDGER-AND-ROLLBACK.md`, `scripts/refactor_characterization_gate.py`
3. **`shadow-concurrency/`**: `SKILL.md`, `methodologies/DURABLE-ASYNC-OUTBOX-AND-IDEMPOTENCY.md`, `playbooks/STATE-MACHINE-AND-FAILURE-MATRIX.md`, `scripts/concurrency_invariant_checker.py`
4. **`shadow-domain/`**: `SKILL.md`, `methodologies/DDD-BOUNDED-CONTEXTS-AND-AGGREGATES.md`, `playbooks/INVARIANT-CATALOG-AND-STATE-SPEC.md`, `scripts/domain_invariant_verifier.py`
5. **`shadow-realtime/`**: `SKILL.md`, `methodologies/WEBSOCKET-SSE-RESUMPTION-AND-BACKPRESSURE.md`, `playbooks/REALTIME-PROTOCOL-ADR-AND-RUNBOOK.md`, `scripts/realtime_transport_verifier.py`
6. **`shadow-search/`**: `SKILL.md`, `methodologies/HYBRID-BM25-VECTOR-RRF-AND-ACL.md`, `playbooks/SEARCH-RELEVANCE-AND-MIGRATION-PLAYBOOK.md`, `scripts/search_relevance_acl_gate.py`
7. **`shadow-supplychain/`**: `SKILL.md`, `methodologies/SBOM-SLSA-PROVENANCE-AND-LOCKFILE-INTEGRITY.md`, `playbooks/SBOM-RISK-REGISTER-AND-ATTESTATION.md`, `scripts/supplychain_sbom_gate.py`

## 3. Enhancement Reports (`14` Files)
`reports/shadow-enhancement/2026-11-16-SA-SE-ENH-001/`:
- Phase 0 (`7`): `inventory.md`, `capability-gap-matrix.md`, `overlap-and-boundaries.md`, `risk-register.md`, `implementation-plan.md`, `source-register.md`, `baseline-test-report.md`
- Phase 5 (`7`): `implementation-summary.md`, `changed-files-manifest.md`, `routing-test-report.md`, `skills-test-report.md`, `cross-agent-compatibility.md`, `unresolved-issues.md`, `rollout-and-rollback.md`
