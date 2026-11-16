# Phase 0 — Phased Implementation Plan (`SA-SE-ENH-001`)

1. **Phase 0 (`G0`) [DONE]:** Baseline inspection (`185c42a`), inventory, gap matrix, overlap analysis, risk register, baseline test report, source register.
2. **Phase 1 (`G1`) — Foundation, Debugging & Refactoring `[P0]`:**
   - Enhance `shadow-monarch/SKILL.md`, `shadow-monarch/GLOBAL.md`, `shadow-monarch/scripts/skill_router.py` (Repository-Native Protocol + §2.2 Router Decision Record + 52-skill registry).
   - Create `shadow-debug/` (skill + methodology + playbook + `debug_hypothesis_gate.py`) and `shadow-refactor/` (skill + methodology + playbook + `refactor_characterization_gate.py`).
   - Deepen `shadow-quality`, `shadow-test`, `shadow-architect`.
3. **Phase 2 (`G2`) — Backend Correctness, Concurrency & Domain `[P0/P1]`:**
   - Create `shadow-concurrency/` (+ `concurrency_invariant_checker.py`) and `shadow-domain/` (+ `domain_invariant_verifier.py`).
   - Deepen `shadow-auth`, `shadow-data`, `shadow-db`, `shadow-api`, `shadow-cache`, `shadow-integrate`.
4. **Phase 3 (`G3`) — Realtime Transport & Production Resilience `[P1]`:**
   - Create `shadow-realtime/` (+ `realtime_transport_verifier.py`).
   - Deepen `shadow-perf`, `shadow-observe`, `shadow-ops`, `shadow-resilience`, `shadow-maintain`.
5. **Phase 4 (`G4`) — Search & Supply-Chain Integrity `[P1]`:**
   - Create `shadow-search/` (+ `search_relevance_acl_gate.py`) and `shadow-supplychain/` (+ `supplychain_sbom_gate.py`).
   - Deepen `shadow-eval`, `shadow-sec`, `shadow-compat`, `shadow-git`, `shadow-release`.
6. **Phase 5 (`G5`) — Eval Expansion (`28 -> 35`), Cross-Agent Smoke & Final Report Bundle:**
   - Update `README.md`, `install.ps1`, `install.sh`, `shadow-monarch.zip` locally; test `install-codex.ps1` in `$env:TEMP` only.
   - Add Evals `#29`–`#35` to `evals/evals.json`, `evals/README.md`, `evals/run_evals.py`.
   - Execute full L0–L5 verification suite and write remaining 7 final reports (`§10.2`).

## Rollback Plan
Because no global home directories or Git remotes are mutated during execution, full rollback to commit `185c42a` is cleanly achieved via:
- Removing the 7 new skill directories (`shadow-debug`, `shadow-concurrency`, `shadow-refactor`, `shadow-domain`, `shadow-search`, `shadow-realtime`, `shadow-supplychain`) and `reports/shadow-enhancement/2026-11-16-SA-SE-ENH-001/`
- Reverting modified tracked files via `git checkout -- .` (only if explicitly requested by the Monarch).
