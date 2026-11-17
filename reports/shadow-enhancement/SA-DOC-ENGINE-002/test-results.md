# SA-DOC-ENGINE-002 — Automated Verification Results (`G5`)

Generated: 2026-11-17

| Suite / Command | Total Cases | PASS | FAIL | BLOCKED | NOT_RUN | Exit Code | Notes & Evidence |
|---|---|---|---|---|---|---|---|
| `python shadow-doc/scripts/doc_engine_test_suite.py` | 58 | 58 | 0 | 0 | 0 | 0 | Tests `1..44` + `T45..T58` hardening probes (`R01`–`R08`, `H01`–`H03`) in isolated temp fixtures |
| `python shadow-doc/scripts/doc_orchestrator.py --self-test` | 5 | 5 | 0 | 0 | 0 | 0 | Local-first resolution, invalid explicit refusal, PDF-only rejection, traversal/overwrite block, global fallback |
| `python shadow-doc/scripts/doc_scaffold.py --selftest` | 1 | 1 | 0 | 0 | 0 | 0 | `v1.0` compat + library availability (`python-docx`, `openpyxl`, `fpdf2` AVAILABLE; `reportlab`, `markdown` MISSING); `supported_v2_templates: 26` |
| `python shadow-doc/scripts/doc_scaffold.py --acceptance-suite` | 16 | 16 | 0 | 0 | 0 | 0 | `AT-01..AT-15` + scale benchmark with real `pypdf` PDF parsing & DOCX XML checks (`shadow-doc/output/acceptance_report_v2.json`) |
| `python shadow-doc/scripts/reference_verifier.py --self-test` | 10 | 10 | 0 | 0 | 0 | 0 | 7-point file safety & arXiv preprint precision/recall probes |
| `CLI export authorization test` (isolated temp script) | 3 | 3 | 0 | 0 | 0 | 0 | `new_local_exit=0`, `overwrite_no_approval_exit=1` (`BLOCKED_MISSING_APPROVAL`), `overwrite_with_approval_exit=0` |
| `python shadow-monarch/scripts/skill_router.py --audit-descriptions` | 52 skills | 52 | 0 | 0 | 0 | 0 | All 52 `SKILL.md` frontmatter triggers verified (`<=500` chars) |
| `python shadow-monarch/scripts/skill_router.py --self-test` | 38 | 38 | 0 | 0 | 0 | 0 | Includes `DOC-ENGINE-1` (`shadow-doc` + `shadow-grc`) |
| `python evals/run_evals.py --self-test` | 48 | 48 | 0 | 0 | 0 | 0 | Precision/recall across 38 evals (`total_evals_in_catalog: 38`) |
| `python shadow-quality/scripts/shadow_gate.py --repo . --probes-verified` | 7 files | - | 0 | 0 | 0 | 0 | `execution_approval_gate_verified: true`, `official_first_gate_verified: true`, `document_engine_gate_verified: true`, `recommended_max_readiness: "VERIFIED-LOCAL"` |
| `*/SKILL.md <= 500 lines check` | 52 files | 52 | 0 | 0 | 0 | 0 | `SKILL_MD_OVER_500: []` |

## Explicit `NOT_RUN` / Host-Specific Boundaries
- Live external Node `mmdc` binary execution: `mmdc` not installed globally on host; subprocess lifecycle (success SVG, non-zero exit, timeout, corrupt output, missing binary) verified deterministically via isolated Python subprocess test doubles (`T54`).
- `T57` NTFS symlink ancestor enforcement: verified via code inspection of `os.islink` walk and tested inside `doc_engine_test_suite.py`; note that unprivileged Windows shells without Developer Mode may report `NOT_RUN` if `os.symlink` privilege is denied by Windows — in the latest run on this host `T57` executed and reported `PASS` (`ancestor symlink blocked`).
- Cross-platform Linux/macOS execution and global `./install.ps1` / `git push`: `NOT_RUN` awaiting explicit authorization.
