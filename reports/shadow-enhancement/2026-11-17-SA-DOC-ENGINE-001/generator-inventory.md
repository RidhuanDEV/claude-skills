# SA-DOC-ENGINE-001 — Generator Inventory (`G0`)

Generated: 2026-11-17  
Scope: `<repo>`

## 1. Existing Document Generation Infrastructure in Repository

| Component | Path | Type | Status | Capabilities Observed |
|---|---|---|---|---|
| **Shadow Doc Core CLI** | `shadow-doc/scripts/doc_scaffold.py` | Python CLI (`v2.0.0`) | Working (baseline pass) | Subcommands: `create`, `import`, `update`, `validate`, `diff`, `impact`, `approve`, `export`, `package`, `inspect`, `migrate-v1`, `--selftest`, `--acceptance-suite` |
| **Canonical AST & Importer Core** | `shadow-doc/scripts/v2_core.py` | Python module | Working | AST v2.0 + v1.0 compat (`bagian->subbagian->blok`), 20 SDLC templates (`TEMPLATE_MAP`), secret redaction, optimistic concurrency hash, traceability/impact graph |
| **Multi-Format Renderers** | `shadow-doc/scripts/v2_renderers.py` | Python module | Working (partial formats) | Renders `.md`, `.docx` (`python-docx`), `.pdf` (`fpdf2`), `.xlsx` (`openpyxl`), `.csv`, `.zip` (`manifest.json` + SHA-256). Missing: `.html`, DBML handling, external Mermaid vector render |
| **Reference Safety Verifier** | `shadow-doc/scripts/reference_verifier.py` | Python CLI/module | Working (10/10 self-test) | 7-point downloaded reference verification (extensions, magic bytes, PDF `/JavaScript`/`/Launch`, `<script>` check, quarantine delete, `references_manifest.json`) |
| **Canonical AST Schema** | `shadow-doc/schemas/canonical-document.schema.json` | JSON Schema Draft 2020-12 | Working (`v2.0`) | Validates `schema_version: "2.0"`, 7 block kinds (`heading`, `paragraph`, `table`, `figure`, `list`, `code`, `opaque`), `sources[]`, `history[]` |
| **SDLC Templates (`01..20`)** | `shadow-doc/templates/*.md` | Markdown blueprints | Present (20 files) | `01_SDLC_PLAN.md` through `20_DEPLOYMENT.md` |
| **Docs Pipeline Reference** | `shadow-monarch/reference/DOCS-PIPELINE.md` | Reference guide | Present | Defines source-of-truth `.md`/JSON -> `.docx`/`.pdf` rules |
| **Specs & DOCX Code Guide** | `shadow-monarch/reference/sub-SPECS-DOCX-CODE.md` | Reference guide | Present | Defines OpenAPI 3.1, DBML, strict Mermaid, `python-docx`/Node `docx` style rules |

## 2. Specialist Consulting & Delivery Engines Audited

| Skill | Engine Script | Current Document Capability | Overlap / Gap |
|---|---|---|---|
| `shadow-handover` | None (skill instructions only) | References `/shadow-doc` for BAST/Manuals | Needs orchestration + asset/credential handover payload bridge without hardcoded CLI assumptions |
| `shadow-pmo` | `shadow-pmo/scripts/pmo_governance_engine.py` | Outputs JSON only (PERT/CPM/Monte Carlo/EVM/CR) | No adapter converting PMO JSON -> structured document report (`PROJECT_REPORT` / `CHANGE_REQUEST`) |
| `shadow-grc` | `shadow-grc/scripts/grc_assurance_engine.py` | Outputs JSON only (COBIT 2019, ISO 27001 SoA, 6-part findings) | No adapter converting GRC JSON -> `GRC_ASSESSMENT` report |
| `shadow-presales` | `shadow-presales/scripts/presales_commercial_engine.py` | Outputs JSON only (3-scenario capacity, TCO/NPV/RAB) | No adapter converting Presales JSON -> `PRESALES_PROPOSAL` report |
| `shadow-ea` | `shadow-ea/scripts/ea_portfolio_engine.py` | Outputs JSON only (TIME rationalization, 6-domain SPBE) | No adapter converting EA JSON -> `ARCHITECTURE_REPORT` |

## 3. Baseline Test Execution Observed (`G0`)
- `python shadow-doc/scripts/doc_scaffold.py --selftest`: `PASS` (`python-docx`, `openpyxl`, `fpdf2` AVAILABLE; `reportlab`, `markdown` MISSING)
- `python shadow-doc/scripts/doc_scaffold.py --acceptance-suite`: `PASS` (`16/16` passed)
- `python shadow-doc/scripts/reference_verifier.py --self-test`: `PASS` (`10/10` probes passed)
