# SA-DOC-ENGINE-001 — Risk Register (`G0`)

| Risk ID | Risk Description | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| **RSK-DOC-01** | Upgrading AST to `2.1` breaks existing `v1.0` or `v2.0` documents/acceptance suite | Medium | High | Support both `"2.0"` and `"2.1"` in schema & `validate_schema_v2`; run full `--selftest` + `16/16` acceptance suite after edits |
| **RSK-DOC-02** | Generator discovery misclassifies unrelated build scripts (`scripts/build.js`) as compatible doc generators | Medium | Medium | Evaluate via 15 structured criteria (`COMPATIBLE`/`PARTIALLY_COMPATIBLE`/`INCOMPATIBLE`/`UNKNOWN`); never classify solely on filename or PDF emission |
| **RSK-DOC-03** | Path traversal or accidental overwrite destroys user documents or writes outside repo | Medium | Critical | Enforce containment inside resolved allowed root (`Path.relative_to`) and fail closed when destination exists without explicit `--overwrite` |
| **RSK-DOC-04** | Mermaid/DBML external CLI (`mmdc`, `dbml`) absent in target environment | High | Low | Preserve source Mermaid/DBML cleanly in all formats, detect CLI via `shutil.which`, report explicit limitation in `build-manifest.json` & test output (`NOT_RUN`/`BLOCKED` vs silent fake pass) |
| **RSK-DOC-05** | `fpdf2` Core Helvetica font drops non-ASCII characters via `_ascii_clean` | Known | Medium | Document explicitly in `RENDERER_CONTRACTS` & `known-limitations.md`; sanitize predictably without crashing |
| **RSK-DOC-06** | Global config (`~/.claude`, `~/.gemini`, `~/.codex`) or repo git mutated without Monarch approval | Low | Critical | Keep all edits strictly inside local repository working tree; defer `install.ps1` and `git commit`/`push` until explicit authorization |
