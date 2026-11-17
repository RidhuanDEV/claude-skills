# SA-DOC-ENGINE-001 — Migration & Rollback Guide

## 1. Backward Compatibility Guarantees
- **Canonical AST `v1.0` (`bagian -> subbagian -> blok`)**: 100% preserved via `parse_markdown_to_ast`, `validate_ast`, and `migrate-v1` (creates `.v1.bak.json` backup automatically).
- **Canonical AST `v2.0`**: 100% accepted alongside `v2.1` (`SUPPORTED_SCHEMA_VERSIONS = {"2.0", "2.1"}`). Existing `v2.0` documents continue validating and exporting with zero changes required.
- **Project-Native Formats**: Repositories using Markdown, Pandoc, Node `docx`, `python-docx`, or custom build scripts remain untouched and do NOT migrate to JSON AST unless explicitly authorized (`Option D`).

## 2. Opt-In Schema Upgrade (`v2.0` -> `v2.1`)
```powershell
python "shadow-doc/scripts/doc_scaffold.py" migrate-schema --in docs/SRS.json --to 2.1 --out docs/SRS.v21.json
```
Adds `code_refs`, `git_commits`, `rendering_hints`, `schema_migration`, and an entry in `history[]` with `before_hash` / `after_hash` while keeping source file intact.

## 3. Rollback Procedure
- Schema rollback: Since `migrate-schema` writes to `--out`, retain original `.json` (or run `migrate-schema --to 2.0`).
- Document export rollback: Exports never overwrite existing files without `--overwrite`, and `atomic_write_json` writes `.bak` + `.tmp` atomically.
- Repository code rollback: All changes are modular (`doc_orchestrator.py`, `domain_adapters.py`, `doc_engine_test_suite.py`, templates `21..25`, and incremental hooks in `v2_core.py`, `v2_renderers.py`, `doc_scaffold.py`).
