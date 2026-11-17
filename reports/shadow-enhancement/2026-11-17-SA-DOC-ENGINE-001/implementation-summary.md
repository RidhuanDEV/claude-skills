# SA-DOC-ENGINE-001 — Final Implementation Summary (`G5`)

## Architecture Implemented
Shadow Army's document pipeline now enforces **Generator-Agnostic Discovery & Existing-Generator-First Reuse**:
1. **Discovery & Resolution Layer** (`shadow-doc/scripts/doc_orchestrator.py`):
   - Discovers project generators via manifests (`package.json`), Python/Node/shell scripts anywhere in repo, `.shadow/document-engine.json`, templates, and system CLIs (`pandoc`, `typst`, `mmdc`, etc.).
   - Distinguishes all 8 path roles cleanly (`generator_source_dir`, `executable_path`, `global_config_dir`, `project_config_path`, `template_dir`, `input_dir`, `output_dir`, `temp_dir`).
   - Resolves in strict precedence: `1. Explicit User Selection -> 2. Project-Local Discovery -> 3. Project Config -> 4. Global Engine Fallback -> 5. User Decision Gate (Options A/B/C/D)`.
   - Evaluates 15 criteria into `COMPATIBLE | PARTIALLY_COMPATIBLE | INCOMPATIBLE | UNKNOWN`.
2. **Structured Document Core (`v2.0` + `v2.1`)** (`shadow-doc/schemas/canonical-document.schema.json`, `shadow-doc/scripts/v2_core.py`):
   - Added `finding` (6-part defensible structure), `decision-matrix`, `appendix`, `ordered` list flag, `figure_data.diagram_type` (`mermaid | dbml | image`), `evidence_refs`, `code_refs`, `git_commits`, `rendering_hints`, `x-*` namespaced `extensions`, explicit `SCHEMA_UNSUPPORTED_NODE` validation errors, `normalize_document_v2`, and `migrate_schema_version`.
3. **Multi-Format Rendering & Safety** (`shadow-doc/scripts/v2_renderers.py`, `shadow-doc/scripts/doc_scaffold.py`):
   - Added accessible semantic HTML renderer (`render_v2_to_html`), explicit DBML/Mermaid preservation + `render_diagram_asset` CLI check, formal `RENDERER_CONTRACTS`, `templates/registry.json` + templates `21..25` (`GRC_ASSESSMENT`, `PROJECT_REPORT`, `PRESALES_PROPOSAL`, `ARCHITECTURE_REPORT`, `TECH_AUDIT`), traversal guard (`validate_safe_path`), non-overwrite guard (`check_output_overwrite_safety`), and `build-manifest.json` emission.
4. **Cross-Skill Integration & Gate** (`shadow-doc/scripts/domain_adapters.py`, specialist `SKILL.md`s, `skill_router.py`, `shadow_gate.py`, `evals/`):
   - Bridged `shadow-handover`, `shadow-pmo`, `shadow-grc`, `shadow-presales`, and `shadow-ea` into shared adapters without duplicating renderers; wired `doc_orchestrator.py --self-test` into `shadow_gate.py`.
