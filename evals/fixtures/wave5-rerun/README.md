# Wave 5 follow-up re-measurement (2026-11-28)

Re-measures the seven skills that showed no uplift in `../wave5-behavioral`, plus shadow-video, after their fixes. Each skill reruns its original failing scenario (where one existed) and/or a harder scenario from its own `evaluations.md`.

- `scenarios.json`: 13 scenarios with criteria, red flags and the A/B assignment (seed 20261128).
- `answers-baseline.json`: written by an agent with no repository access.
- `answers-skill.json`: written after reading the skill's `SKILL.md` and at most 2 of its references.
- `judge-pack.json` and `judge-output-1.json`: blind judging of all 13.
- Round 2: R05 (shadow-compat) and R12 (shadow-illustration) scored 8 and exposed real gaps: consumer inventory and replay were buried in the browser rule, and there was no tracing playbook. After those fixes, `answers-skill-2.json` was written fresh for those two. The baseline answers were reused unchanged. `judge-pack-2.json` and `judge-output-2.json` hold the re-judged items, which override round 1 for R05 and R12.
- `excluded.json`: empty, so nothing is excluded.

Score with `python evals/score_behavioral_uplift.py --fixtures evals/fixtures/wave5-rerun`.
