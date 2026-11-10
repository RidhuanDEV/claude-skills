---
name: shadow-doc
description: Enterprise & Government SDLC Document Engineering System v2.0 (.docx, .pdf, .xlsx, .csv, .md, .zip) using a Canonical JSON AST v2.0 + Hybrid v1.0 Backward-Compatible Importer. Supports 20 standardized SDLC templates, selective block updates, bidirectional requirement traceability, change-impact analysis, approval lifecycle governance, secret scanning, and multi-format rendering. Trigger with /shadow-doc.
---

# Shadow Doc v2.0 (`/shadow-doc`) — Enterprise & Institutional SDLC Document Engineering System

Use this skill whenever the **Monarch** asks to create, import, selectively update, validate, trace, approve, render, or package formal SDLC, enterprise, or government documents (`.docx`, `.pdf`, `.xlsx`, `.csv`, `.md`, `.json`, `.zip`).

---

## 1. Non-Negotiable Golden Laws (v2.0 + v1.0 Hybrid)

1. **NEVER Edit Binary Outputs Directly (`.docx`, `.xlsx`, `.pdf`)**:
   - All text, tables, diagrams, and metadata changes MUST be applied to the Canonical JSON AST (`.json`) or Markdown source (`.md`) and regenerated via `scripts/doc_scaffold.py`.
2. **Zero Fabricated Facts & Evidence-Backed Claims (`DOC-FR-012`, `DOC-FR-020`, `AT-09`)**:
   - Never invent dates, ticket IDs, metrics, stakeholder names, test results, or deployment topologies. Unknown facts MUST remain explicit placeholders (`[ISI ...]`, `[TBD]`, `UNVERIFIED`).
   - Any block claiming `PASS`, `APPROVED`, `DEPLOYED`, or `CLOSED` MUST cite a verified `source_refs` entry. Strict validation (`validate --strict`) blocks release if unresolved placeholders or unverified claims exist.
3. **Approved Document Protection & Separation of Duties (`DOC-FR-010`, `DOC-FR-011`, `AT-04`, `AT-11`)**:
   - Documents in `APPROVED` or `RELEASED` status are immutable in-place. Calling `update` on an approved document automatically forks a new `DRAFT` revision (e.g., `1.1-DRAFT`) with `supersedes` pointing to the approved revision.
   - Document `owner` cannot self-approve (`owner != approver`), and `HANDOVER` / `BAST` artifacts cannot transition to `APPROVED`/`RELEASED` without signed `evidence_ref`.
4. **Selective Block Updates & Optimistic Concurrency (`DOC-FR-007`, `AT-03`, `AT-07`)**:
   - Partial updates target a specific `scope_id` (e.g., `FR-001`) without mutating unrelated blocks, recording `before_hash` and `after_hash` in `history[]`. Concurrent edits with a stale `expected_hash` fail closed (`CONCURRENCY_CONFLICT`).
5. **Secret Scanning, Cross-Project Isolation & Atomic Rollback (`AT-06`, `AT-10`, `AT-14`)**:
   - All exports automatically redact leaked credentials (`[REDACTED_SECRET]`), reject cross-project `forbidden_terms`, and write files atomically via `.tmp` + `.bak` rollback.
6. **100% v1.0 Backward Compatibility (`AT-12`)**:
   - Legacy v1.0 commands (`--selftest`, `md-to-json`, `check-readiness`) and `bagian -> subbagian -> blok` JSON files remain fully supported and can be migrated losslessly via `migrate-v1` (preserving a `.v1.bak.json` backup).
7. **Research & Normative Standards Source Policy (`NORMATIVE_STANDARDS_MAP`)**:
   - **Industry Standards First**: Every SDLC document (`SRS`, `SDD`, `RTM`, `TEST_PLAN`, `UAT`, `SECURITY_RISK`, `INCIDENT`, `MANUAL`, `MAINTENANCE`) anchors to authoritative standards (`ISO/IEC/IEEE 29148:2018`, `ISO/IEC/IEEE 42010:2022`, `ISO/IEC/IEEE 29119`, `ISO/IEC 25010`, `NIST SSDF SP 800-218`, `OWASP ASVS 5.0.0`, `ISO/IEC/IEEE 12207`, `NIST SP 800-61`, `ISO/IEC/IEEE 14764`, `ISO/IEC/IEEE 26514`) and official version-matched framework documentation (`/context7` MCP).
   - **Academic Literature & `arXiv` Preprint Rules**: Use peer-reviewed databases (`IEEE Xplore`, `ACM Digital Library`, `SpringerLink`, `ScienceDirect`, indexed via `Semantic Scholar` / `OpenAlex` / `Google Scholar`) as supporting evidence when architectural or algorithmic decisions require empirical backing. Never default to `arXiv` for software engineering standards; `arXiv` preprints must be tagged `source_type: "PREPRINT"` (`peer_reviewed: false`) unless a peer-reviewed journal/conference DOI is verified.

---

## 2. Catalog of 20 Standardized SDLC Templates (`templates/01..20`)

All 20 templates live in [`templates/`](templates/) and are cataloged in [`TEMPLATE_CATALOG.md`](TEMPLATE_CATALOG.md):

| # | Type Code | Template File | Document Title | Primary SDLC Stage | Collaborating Skill |
|---|---|---|---|---|---|
| 01 | `SDLC_PLAN` | `01_SDLC_PLAN.md` | Software Development Lifecycle Plan | Discovery / Planning | `/shadow-plan` |
| 02 | `BRD_PRD` (`PRD`, `BRD`) | `02_BRD_PRD.md` | Business and Product Requirements | Discovery | `/shadow-discovery` |
| 03 | `SRS` | `03_SRS.md` | Software Requirements Specification | Discovery | `/shadow-discovery` |
| 04 | `SDD` | `04_SDD.md` | Software Design Document | Architecture | `/shadow-architect`, `/shadow-design` |
| 05 | `ADR` | `05_ADR.md` | Architecture Decision Record | Architecture | `/shadow-architect` |
| 06 | `JUKNIS` | `06_JUKNIS.md` | Technical Implementation & Operations Guide | Implementation / Ops | `/shadow-ops`, `/shadow-api` |
| 07 | `CONFIG` | `07_CONFIG.md` | Configuration Register | Implementation / Release | `/shadow-ops`, `/shadow-sec` |
| 08 | `RTM` | `08_RTM.md` | Requirements Traceability Matrix | Verification / UAT | `/shadow-test`, `/shadow-uat` |
| 09 | `TEST_PLAN` | `09_TEST_PLAN.md` | Software Test Plan and Execution Report | Verification / Pre-UAT | `/shadow-test`, `/shadow-perf` |
| 10 | `UAT` | `10_UAT.md` | User Acceptance Test Plan and Report | Staging UAT | `/shadow-uat` |
| 11 | `BUG_LOG` | `11_BUG_LOG.md` | Defect and Bug Register | Verification / UAT | `/shadow-test`, `/shadow-uat` |
| 12 | `CHANGE_REQUEST` (`CR`) | `12_CHANGE_REQUEST.md` | Change Request and Impact Assessment | Cross-Stage Governance | `/shadow-plan`, `/shadow-architect` |
| 13 | `CHANGELOG` | `13_CHANGELOG.md` | Change Log and Release Notes | Production Release | `/shadow-release` |
| 14 | `INCIDENT` | `14_INCIDENT.md` | Production Incident Report and RCA | Post-Prod Maintenance | `/shadow-maintain`, `/shadow-observe` |
| 15 | `CAPA` | `15_CAPA.md` | Corrective Action & Improvement Recommendations | Post-Prod Maintenance | `/shadow-maintain`, `/shadow-resilience` |
| 16 | `MANUAL` | `16_MANUAL.md` | User, Administrator and Operator Manual | Client Handover | `/shadow-handover` |
| 17 | `HANDOVER` (`BAST`) | `17_HANDOVER.md` | Handover Package / BAST Annex | Client Handover | `/shadow-handover` |
| 18 | `SECURITY_RISK` | `18_SECURITY_RISK.md` | Security Assessment and Risk Register | Verification / Security | `/shadow-sec`, `/shadow-auth` |
| 19 | `MAINTENANCE` | `19_MAINTENANCE.md` | Maintenance and Service Level Report | Post-Prod Maintenance | `/shadow-maintain` |
| 20 | `DEPLOYMENT` | `20_DEPLOYMENT.md` | Deployment and Production Verification Record | Production Release | `/shadow-release`, `/shadow-ops` |

---

## 3. Ownership Boundaries Across Shadow Army Skills (Zero Duplication)

- **Domain Skills Generate Technical Truth**:
  - `/shadow-discovery` elicits requirements & acceptance criteria -> feeds `BRD_PRD` & `SRS`.
  - `/shadow-architect` & `/shadow-db` design C4, ADRs, and DB schemas -> feed `SDD` & `ADR`.
  - `/shadow-test`, `/shadow-sec`, & `/shadow-perf` execute tests, security audits, and Pre-UAT load tests -> feed `TEST_PLAN`, `BUG_LOG`, & `SECURITY_RISK`.
  - `/shadow-uat` governs UAT scenarios & sign-off -> feeds `RTM` & `UAT`.
  - `/shadow-release` & `/shadow-ops` execute deployments & runbooks -> feed `CHANGELOG`, `DEPLOYMENT`, & `JUKNIS`.
  - `/shadow-handover` & `/shadow-maintain` govern BAST delivery, SLAs, and RCAs -> feed `HANDOVER`, `MANUAL`, `INCIDENT`, `CAPA`, & `MAINTENANCE`.
- **`/shadow-doc` v2.0 Owns Canonical AST Governance & Multi-Format Rendering**:
  - `/shadow-doc` owns schema validation (`schemas/canonical-document.schema.json`), selective block patching, cross-document traceability/impact graphs, approval state transitions, and deterministic rendering to `.docx`, `.pdf`, `.xlsx`, `.csv`, `.md`, and `.zip`.

---

## 4. CLI Reference (`scripts/doc_scaffold.py`)

```powershell
# 1. Create a canonical v2.0 JSON document from any of the 20 templates
python "d:\Ridhuan Ngoding Moment\SKILL\shadow-doc\scripts\doc_scaffold.py" create `
  --type SRS --project-id PRJ-2026 --doc-id DOC-SRS-001 `
  --lang id-ID --style corporate --owner "System Analyst" --out docs/SRS.json

# 2. Import existing .md, .docx, .pdf (reference), or legacy v1 .json into v2.0 AST
python "d:\Ridhuan Ngoding Moment\SKILL\shadow-doc\scripts\doc_scaffold.py" import `
  --in draft.md --project-id PRJ-2026 --type SRS --doc-id DOC-SRS-001 --out docs/SRS.json

# 3. Selectively update a single block (auto-forks new DRAFT if document is APPROVED)
python "d:\Ridhuan Ngoding Moment\SKILL\shadow-doc\scripts\doc_scaffold.py" update `
  --doc docs/SRS.json --scope-id FR-001 `
  --content "Sistem wajib mendukung OAuth2/OIDC dengan FIDO2 Passkey." `
  --author "Security Architect" --change-ref CR-001

# 4. Validate schema, secrets, traceability, and release gates (--strict for release)
python "d:\Ridhuan Ngoding Moment\SKILL\shadow-doc\scripts\doc_scaffold.py" validate --doc docs/SRS.json --strict

# 5. Bidirectional traceability & change-impact analysis
python "d:\Ridhuan Ngoding Moment\SKILL\shadow-doc\scripts\doc_scaffold.py" impact `
  --doc docs/SRS.json docs/RTM.json --changed-id FR-001

# 6. Controlled approval transition (enforces owner != actor & evidence_ref)
python "d:\Ridhuan Ngoding Moment\SKILL\shadow-doc\scripts\doc_scaffold.py" approve `
  --doc docs/SRS.json --status APPROVED --actor "VP Engineering" `
  --role "Approver" --evidence-ref "MINUTES-2026-11-10"

# 7. Export to DOCX, PDF, XLSX, CSV, and Markdown with automated cross-format QA
python "d:\Ridhuan Ngoding Moment\SKILL\shadow-doc\scripts\doc_scaffold.py" export `
  --doc docs/SRS.json --format all --out-dir docs/output

# 8. Build stage handover ZIP bundle with SHA-256 manifest.json
python "d:\Ridhuan Ngoding Moment\SKILL\shadow-doc\scripts\doc_scaffold.py" package `
  --source-dir docs/output --project-id PRJ-2026 --stage handover --out docs/Handover_Bundle.zip

# 9. Run v1.0 backward-compatibility self-test & v2.0 15-test acceptance suite
python "d:\Ridhuan Ngoding Moment\SKILL\shadow-doc\scripts\doc_scaffold.py" --selftest
python "d:\Ridhuan Ngoding Moment\SKILL\shadow-doc\scripts\doc_scaffold.py" --acceptance-suite
```

- **Word TOC Field Note**: When opening generated `.docx` files in Microsoft Word, press `Ctrl+A` then `F9` to populate dynamic page numbers in the native Word Table of Contents (`TOC`) field.
- **References**:
  - Canonical Schema: [`schemas/canonical-document.schema.json`](schemas/canonical-document.schema.json)
  - Hybrid Schema & Migration Reference: [`references/HYBRID-JSON-MD-SCHEMA.md`](references/HYBRID-JSON-MD-SCHEMA.md)
  - Full PRD/SRS Requirements: [`requirements/SHADOW_DOC_V2_PRD_SRS.md`](requirements/SHADOW_DOC_V2_PRD_SRS.md)
