# SA-DOC-ENGINE-001 — Architecture Proposal & Decision Records (`G0`)

Generated: 2026-11-17

## ADR-DOC-001: Incremental Upgrade Over Rewrite
- **Context:** `shadow-doc/scripts/` already provides 16/16 verified `AT-01..AT-16` acceptance coverage (`v2_core.py`, `v2_renderers.py`, `doc_scaffold.py`, `reference_verifier.py`).
- **Decision:** Keep and extend `shadow-doc` incrementally rather than creating a separate `shadow-document-engine/` directory or rewriting `v2_core.py`.
- **Consequences:** Preserves 100% backward compatibility with `v1.0` and `v2.0` schemas/CLIs while adding `doc_orchestrator.py` and `v2.1` capabilities cleanly.

## ADR-DOC-002: Generator-Agnostic Precedence & Local-Generator-First Policy
- **Decision:** Introduce `shadow-doc/scripts/doc_orchestrator.py` implementing deterministic resolution:
  `1. Explicit User Selection -> 2. Project-Local Discovery -> 3. Project Config (.shadow/document-engine.json) -> 4. Global Engine Fallback (shadow-doc) -> 5. User Decision Gate (Options A/B/C/D)`.
- **Consequences:** Existing project pipelines (Pandoc, Node `docx`, `python-docx`, MkDocs, custom build scripts) are discovered, classified across 15 criteria, and reused directly or bridged via non-destructive adapters instead of forced migration.

## ADR-DOC-003: Schema `2.0` + `2.1` Coexistence & Non-Forced Source-of-Truth
- **Decision:** Accept both `schema_version: "2.0"` and `"2.1"` in `canonical-document.schema.json` and `v2_core.py`. JSON AST is strictly the internal canonical representation **only when using the Global Document Engine**; existing repositories keep Markdown, YAML, or project-native formats as their source of truth.
- **Consequences:** Zero forced migrations; supports structured `finding`, `decision-matrix`, `appendix`, `dbml`, `evidence_refs`, `code_refs`, `git_commits`, `rendering_hints`, namespaced `extensions` (`x-*`), and explicit `SCHEMA_UNSUPPORTED_NODE` errors.

## ADR-DOC-004: Content vs Presentation Separation + Safe Atomic Outputs
- **Decision:** Templates (`templates/registry.json` + `templates/01..25`) and renderers (`RENDERER_CONTRACTS`) isolate layout/branding from semantic AST blocks. Export paths enforce workspace containment (path traversal rejection), non-overwrite by default (`--overwrite` opt-in), atomic writes, and `build-manifest.json` emission.
