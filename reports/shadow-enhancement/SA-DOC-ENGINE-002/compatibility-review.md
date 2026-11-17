# SA-DOC-ENGINE-002 — Compatibility Assessment Review (`R04`)

Generated: 2026-11-17

## 1. Evidence-Backed 15-Criterion Model
All 15 criteria in `doc_orchestrator.py::assess_generator_compatibility` strictly emit `PASS | FAIL | UNKNOWN | NOT_APPLICABLE | ADAPTER_REQUIRED` alongside `criteria_evidence`:

1. `supported_input_formats`, `supported_output_formats`: verified against requested inputs/outputs AND checked for manifest-vs-script `contradictions`.
2. `dependency_compatibility`: verifies Python modules (`importlib.util.find_spec`), Node packages (`package.json`/`node_modules`), and CLI binaries (`shutil.which`); missing runtime dependencies force `FAIL` -> `INCOMPATIBLE`.
3. `security_implications`: statically scans generator scripts (`DANGEROUS_SINK_RE` for `os.system`, `eval`, `exec`, `shell=True`); uninspected candidates stay `UNKNOWN`.
4. `execution_side_effects`, `rendering_quality`, `image_and_asset_handling`: require verification evidence (`verified_source_scan` / Global Engine / QA verified); bare candidates stay `UNKNOWN` (never blind `PASS`).
5. `template_capabilities`, `diagram_rendering`, `source_references_and_citations`: return `ADAPTER_REQUIRED` when gap is bridgeable non-destructively or `NOT_APPLICABLE` when unrequested.

## 2. Verification Evidence
- `T46`: Script importing uninstalled `weasyprint` -> `status="INCOMPATIBLE"`, `dependency_compatibility="FAIL"`.
- `T47`: `.shadow/document-engine.json` declaring `["pdf", "docx"]` backed only by `reportlab` -> `INCOMPATIBLE` with explicit contradiction note.
- `T51`: Bare unverified candidate receives `UNKNOWN` on `security_implications`, `dependency_compatibility`, `execution_side_effects`, `rendering_quality`.
