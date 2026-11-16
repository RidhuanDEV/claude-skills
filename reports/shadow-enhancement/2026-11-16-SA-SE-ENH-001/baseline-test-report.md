# Phase 0 — Baseline Verification Report (`SA-SE-ENH-001`)

Executed on `2026-11-16T11:54:44+07:00` against clean `main` at SHA `185c42a2fa8e520293b3819a56b681fd60b9fe18`.

| Check ID | Scenario / Gate | Command | Exit Code | Result | Observed Evidence |
|---|---|---|---:|---|---|
| `BASE-01` | Repo quality & drift gate | `python "shadow-quality/scripts/shadow_gate.py" --repo .` | `0` | `PASS` | `passed: true`, `0` violations, `0` warnings (`--cleanup-docker-leaks` omitted due to external host container `slos-e2e-db`) |
| `BASE-02` | Frontmatter trigger audit (45 skills) | `python "shadow-monarch/scripts/skill_router.py" --audit-descriptions` | `0` | `PASS` | `total_skills: 45`, `missing_use_when_trigger: []`, `oversized_descriptions_gt_500: []` |
| `BASE-03` | Topic router precision/recall baseline | `python "shadow-monarch/scripts/skill_router.py" --self-test` | `0` | `PASS` | `17/17` probes passed (`all_passed: true`) |
| `BASE-04` | Evals catalog validation | `python "evals/run_evals.py" --validate` | `0` | `PASS` | `valid: true`, `eval_count: 28` |
| `BASE-05` | Eval assertions self-test | `python "evals/run_evals.py" --self-test` | `0` | `PASS` | `28/28` probes passed (`all_passed: true`) |
| `BASE-06` | Consulting intelligence core self-test | `python "shadow-monarch/consulting-core/scripts/consulting_core.py" --self-test` | `0` | `PASS` | `6/6` probes passed (`all_passed: true`) |
| `BASE-07` | Live external CLI execution (`claude`/`codex`) | `evals/run_evals.py --agent ...` | `—` | `NOT_RUN` | Out of Phase 0 read-only baseline scope; no live LLM execution performed |
