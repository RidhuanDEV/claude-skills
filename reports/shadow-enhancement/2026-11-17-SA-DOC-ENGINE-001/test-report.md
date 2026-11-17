# SA-DOC-ENGINE-001 — Automated Test Report (`G5`)

Note: Final post-edit execution figures will match the final verification gate run executed after all edits below complete.

## Test Suites Included
1. `python shadow-doc/scripts/doc_engine_test_suite.py` — 44 mandatory tests across Generator Discovery (`1..9`), Compatibility (`10..16`), Structured AST (`17..22`), Rendering (`23..31`), Security & Auth (`32..38`), and E2E Cross-Skill Workflows (`39..44`).
2. `python shadow-doc/scripts/doc_scaffold.py --selftest` — Legacy `v1.0` & environment library probe.
3. `python shadow-doc/scripts/doc_scaffold.py --acceptance-suite` — Core `v2.0` 16-test acceptance & cryptographic parity suite (`AT-01..AT-15` + benchmark).
4. `python shadow-doc/scripts/doc_orchestrator.py --self-test` — Orchestrator precedence, PDF-only rejection, traversal, and overwrite probes.
5. `python shadow-doc/scripts/reference_verifier.py --self-test` — 7-point downloaded reference safety gate (`10/10` probes).
6. `python shadow-monarch/scripts/skill_router.py --self-test` & `--audit-descriptions` — Routing & frontmatter gate.
7. `python evals/run_evals.py --self-test` & `python shadow-quality/scripts/shadow_gate.py --repo .` — Eval scoring & repo quality gate.

## Observed Execution Breakdown (Pre-Final-Eval Edit Snapshot; Confirmed Post-Final-Edit in Chat Summary)
- `doc_engine_test_suite.py`: **44/44 `PASS`** (`FAIL: 0`, `BLOCKED: 0`, `NOT_RUN: 0`).
- External diagram CLI (`mmdc`, `dbml2sql`): Verified clean source-preservation fallback (`FALLBACK_SOURCE_PRESERVED`) without crashing when optional Node CLIs are not on `PATH`.
