# Phase 0 — Risk Register (`SA-SE-ENH-001`)

| Risk ID | Risk (`§12`) | Likelihood | Impact | Mitigation in Execution | Stop / Escalation Condition |
|---|---|---|---|---|---|
| `RSK-01` | Duplicate or colliding triggers between new and existing skills | Medium | High | Explicit positive/negative `Use when... / Do NOT use for...` frontmatter + negative routing tests across all 52 skills in `skill_router.py` | Stop if any probe activates wrong sibling skill |
| `RSK-02` | Instruction/context bloat crowding out relevant guidance | Medium | High | 3-Layer Progressive Loading (`§2.1`); keep all `SKILL.md` files concise routers (`< 220` lines) with methodologies/playbooks loaded lazily | Stop if `SKILL.md > 500` lines or `description > 500` chars |
| `RSK-03` | External Docker daemon (`slos-e2e-db` on port `55432`) interference | High | Critical | Never run `--cleanup-docker-leaks` or touch external containers; run `shadow_gate.py --repo .` scoped strictly to repo files | Stop immediately if any step proposes mutating host Docker containers |
| `RSK-04` | Unapproved mutation of `~/.gemini`, `~/.claude`, `~/.codex`, `~/.agents` or `git push` | Medium | High | Strictly prohibited during enhancement run (`§0.4`, `§9 Phase 5`); test `install-codex.ps1` only in disposable `$env:TEMP` and delete it cleanly | Stop if any script attempts writing to `$HOME` without user approval |
| `RSK-05` | Weak self-tests checking only keywords/folder existence | Medium | High | Every deterministic script executes positive golden tests, negative/precision probes, property checks, and `§10.1` must-fail fixtures | Stop if any must-fail fixture passes |
| `RSK-06` | Unverified or mixed library version claims in new methodologies | Low | Medium | Anchor versioned references in `source-register.md` and avoid hardcoded unverified threshold magic numbers | Mark missing access as `UNVERIFIED` |
| `RSK-07` | Regressing existing 28 eval scenarios or consulting core | Low | High | Retain and re-run Evals #1–#28 + `consulting_core.py --self-test` alongside new Evals #29–#35 | Stop on any baseline test regression |
| `RSK-08` | Non-portable hardcoded Windows/user paths inside scripts | Medium | Medium | Resolve paths relative to `Path(__file__).resolve()` or CLI args; zero hardcoded `C:\Users\...` or `d:\...` in new code | Stop if `reference_verifier.py` or lint flags non-portable paths |
