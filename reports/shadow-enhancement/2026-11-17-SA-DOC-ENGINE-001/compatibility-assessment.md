# SA-DOC-ENGINE-001 — Compatibility Assessment (`G0`)

Generated: 2026-11-17

## 1. Compatibility Assessment of Existing `shadow-doc` Global Engine (`v2.0` -> `v2.1`)

Evaluated against the 15 mandatory compatibility criteria (`Section 4.1`):

| # | Criterion | Baseline Status (`v2.0`) | Assessment Finding |
|---|---|---|---|
| 1 | Supported input formats | `.md`, `.docx`, `.pdf` (ref), `.json` (v1 & v2) | Preserved; needs v2.1 extended node support |
| 2 | Supported output formats | `.md`, `.docx`, `.pdf`, `.xlsx`, `.csv`, `.zip` | Missing `.html`; `.pdf` via `fpdf2` strips non-ASCII via `_ascii_clean` (known limitation) |
| 3 | Template capabilities | 20 SDLC `.md` blueprints | Lacks consulting/audit/presales/EA/project-report blueprints and registry metadata |
| 4 | Diagram rendering | Mermaid code blocks in MD; plain text fallback in PDF/DOCX | Missing DBML handling & external CLI vector/image embedding (`mmdc`/`@dbml/cli`) |
| 5 | Table rendering | Clean in MD, DOCX (`w:tblHeader`, `w:cantSplit`), XLSX, CSV; pipe text in PDF | Adequate; HTML needs semantic `<table>` rendering |
| 6 | Code-block rendering | Fenced in MD; Consolas monospace in DOCX; Courier in PDF | HTML needs clean `<pre><code>` blocks |
| 7 | Image and asset handling | Figure metadata (`path`, `alt_text`, `caption`) | DOCX/HTML/PDF should resolve relative assets safely & reject path traversal |
| 8 | Source references & citations | `sources[]` + `source_refs` + `reference_verifier.py` | Needs `evidence_refs`, `code_refs`, `git_commits` fields per `Section 6.1` |
| 9 | API/CLI integration | `doc_scaffold.py` argparse CLI | Needs `discover`, `assess`, `resolve`, `migrate-schema` & overwrite/traversal flags |
| 10 | Dependency compatibility | `python-docx`, `openpyxl`, `fpdf2` installed locally | Optional deps (`mmdc`, `pandoc`, `typst`) must degrade gracefully with explicit status |
| 11 | Configuration requirements | Zero project config discovery | Must support `.shadow/document-engine.json` without mutating global config |
| 12 | Execution side effects | Writes `out_dir/<stem>.<ext>` directly; can overwrite silently | Must block silent overwrites unless `--overwrite` explicitly passed |
| 13 | Security implications | Secret redaction + `forbidden_terms` active | Needs output path traversal guard & forbidden script/HTML sanitization in HTML output |
| 14 | Rendering quality | Solid corporate/institutional DOCX & XLSX; basic `fpdf2` ASCII PDF | Keep `fpdf2` offline fallback; document non-ASCII PDF limitation explicitly |
| 15 | Existing project conventions | Enforces Global AST if invoked blindly | Must yield to existing compatible repo generators via discovery precedence |

## 2. Classification Matrix for Supported Generator Profiles

- **`shadow-doc` Global Engine**: `COMPATIBLE` (once HTML, v2.1 AST nodes, DBML, overwrite & traversal guards are added; known PDF non-ASCII limitation documented).
- **Project-local Markdown/Pandoc/Node-`docx`/Python-`python-docx` generators**: Evaluated dynamically per repository using the 15 criteria into `COMPATIBLE`, `PARTIALLY_COMPATIBLE`, `INCOMPATIBLE`, or `UNKNOWN`.
