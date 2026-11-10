# SHADOW-DOC V2 — PRODUCT REQUIREMENTS & IMPLEMENTATION SPECIFICATION

Version: 2.0.0-draft | Language: Bahasa Indonesia | Status: PROPOSED, not implemented

## 1. Tujuan dan batasan
Bangun skill `/shadow-doc` sebagai Enterprise SDLC Documentation & Synchronization Engine, yang mengelola dokumen sepanjang discovery, design, build, verification, release, handover dan maintenance. Skill mengorkestrasi modul existing: monarch, discovery, architect, plan, bootstrap, api, db, auth, test, sec, quality, ops, perf, uat, release, observe, maintain, resilience dan handover.

**In scope:** generation from verified sources; review existing documentation; structured extraction; selective patching; traceability; controlled exports; approval workflow; deterministic schema validation; evidence tracking; audit trail; document packages; diff and impact analysis.
**Out of scope:** menggantikan otoritas persetujuan manusia; mengklaim audit atau sertifikasi standar; otomatis mengubah production; memalsukan dokumen; menyimpan secrets dalam berkas output; mengarang keputusan atau evidence yang tidak ditemukan.

## 2. Design principles
- Source-of-truth canonical AST JSON with stable semantic IDs; Markdown accepted for import/export, DOCX/PDF/XLSX are generated artifacts; original file retained intact and hash-verified.
- Evidence-first: setiap klaim historis atau status test/approval/release memerlukan sumber; jika tidak tersedia -> `UNVERIFIED` / `[PERLU KONFIRMASI]`.
- Preservation: update hanya affected sections, simpan struktur tabel, numbering, page breaks, styles, header/footer, citations dan numbering secara terukur. Render diff before save.
- Human governance: approvals and signatures cannot be inferred; immutable approved snapshot; changes require new revision or change request.
- Least privilege: read-only by default; no live infrastructure changes; redact secrets, access controls, PII and export policies.
- Tool adaptability: work with existing file formats, no new MCP server mandatory; native CLI/libraries optional by environment.
- No mandatory code-wide scan; derive minimal source set and check freshness.

## 3. Pengguna, peran, matriks otorisasi
Roles: Author (draft/update), Reviewer (comment/request changes), Approver (approve controlled revision), Release Manager (publish signed outputs), Auditor (read provenance), Administrator (manage configuration, never auto-approve own generated evidence).
Separation of duties configurable: author != approver for controlled artifacts; approval path can include client and vendor representatives. Agent can prepare but NEVER sign.

## 4. Katalog deliverables wajib
1. SDLC Plan / Software Development Plan
2. BRD/PRD + Stakeholder & Scope Register
3. SRS (Functional + Nonfunctional Requirements)
4. SDD / Software Architecture & Detailed Design
5. ADR (Architecture Decision Record)
6. Interface/API & Database Configuration Specification
7. Technical Instructions / Juknis (deployment/operations/backup/troubleshoot)
8. Configuration Register / Environment Matrix
9. RTM (Requirement Traceability Matrix)
10. Test Plan, Test Case & Test Execution Evidence
11. UAT Plan/Matrix/Report + Sign-off Record
12. Bug/Defect Log
13. Change Request & Change Impact Record
14. Change Log / Release Notes / Deployment Record
15. Incident Report + RCA / Postmortem
16. Corrective and Preventive Action (CAPA) & Improvement Recommendations
17. User/Admin/Operator Manual
18. Handover Checklist / BAST annex & Acceptance Pack
19. Optional Security Assessment & Risk Register
20. Optional Maintenance SLA & Service Report

## 5. Functional requirements (acceptance-verifiable)
| ID | Requirement | Acceptance criteria |
|---|---|---|
| DOC-FR-001 | Project context discovery | Detect repo root, project name, scope and source registry; no guessed facts; list missing artifacts |
| DOC-FR-002 | Select document type | Accept command with document code, project, audience, language, output format and mode |
| DOC-FR-003 | Generate templates | Each catalog template renders with required sections and placeholders marked explicitly |
| DOC-FR-004 | Canonical model | AST validates against versioned JSON schema; round-trip retains stable IDs |
| DOC-FR-005 | Markdown import | Parse headings/tables/IDs; unrecognized content preserved in `unmapped_blocks` for review |
| DOC-FR-006 | Existing document import | Support DOCX / Markdown, ingest PDF as reference; PDF edits via revision export, never assume lossless parsing |
| DOC-FR-007 | Targeted update | Detect affected section IDs, propose patch, preserve unrelated sections and display section-level diff |
| DOC-FR-008 | Impact analysis | Changes in FR/NFR trigger linked SDD/RTM/test/UAT/operations review suggestions |
| DOC-FR-009 | Requirement traceability | Bidirectional links Req -> Design -> Implementation -> Test -> Defect -> Release; orphan warning |
| DOC-FR-010 | Change history | Log who/what/when/reason/source, before/after checksum, version, approval |
| DOC-FR-011 | Controlled approvals | Lifecycle DRAFT -> IN_REVIEW -> APPROVED -> RELEASED -> SUPERSEDED; no auto signoff |
| DOC-FR-012 | Source provenance | Claims include source path/ref + reviewed date; mark unknown status visibly |
| DOC-FR-013 | Multi-format output | DOCX/PDF for narrative, XLSX/CSV for registers, Markdown/JSON for machine-readable; emit validation report |
| DOC-FR-014 | Template styling | Configurable organization branding + standard design tokens; styles accessible, TOC/bookmarks |
| DOC-FR-015 | Document validation | Required sections, unique IDs, broken links, field completeness, language, inconsistent versions |
| DOC-FR-016 | Artifact protection | No secrets, credentials or raw tokens; redact sensitive fields by policy |
| DOC-FR-017 | Versioning | Semantic doc revisions distinct from app versions, explicit baselines and superseded references |
| DOC-FR-018 | Audit-ready export | Produce manifest with hashes, source evidence, generation version, pending issues |
| DOC-FR-019 | Human confirmation | Request approval before overwriting originals, publishing approved revisions, or destructive filesystem ops |
| DOC-FR-020 | Empty-data handling | Never fabricate test pass, timestamps, deployment, incident resolutions, or signer details |
| DOC-FR-021 | Multi-project isolation | namespace per project/client; prevent cross-project content bleed |
| DOC-FR-022 | Incremental rebuild | Regenerate only affected outputs based on dependency graph, source hashes and cache |
| DOC-FR-023 | Cross-format consistency | same values/IDs across generated PDF/DOCX/XLSX/MD for a given revision |
| DOC-FR-024 | Collaborative workflow | Review comments and conflict detection; resolve concurrent edits without silent last-write-wins |
| DOC-FR-025 | Offline compatibility | Generate without internet for local templates and sources; standards references bundled as summaries with attribution |
| DOC-FR-026 | Localization | Indonesian and English labels, dates, captions and terminology configurable |
| DOC-FR-027 | Package delivery | Assemble per-stage package + index, checksum manifest and unresolved issues |
| DOC-FR-028 | Legacy migration | Import existing shadow-doc JSON/MD while retaining backups and migration report |
| DOC-FR-029 | CLI interface | expose create, update, validate, diff, impact, export, package, inspect with dry-run |
| DOC-FR-030 | Safe error behavior | validation errors block release, remain recoverable, no partial overwrite |

## 6. Nonfunctional requirements (targets to verify, not measured results)
| ID | Category | Proposed measurable target |
|---|---|---|
| DOC-NFR-001 | Fidelity | no unapproved loss of existing blocks or styles on target-specific updates; report unsupported constructs |
| DOC-NFR-002 | Determinism | identical canonical revision + template + renderer version -> equivalent content and semantic identifiers |
| DOC-NFR-003 | Performance | <= 10s p95 validation for <= 200 pages on reference hardware (benchmark before commit) |
| DOC-NFR-004 | Security | secret scanner blocks release on critical detections; encrypted transport/storage per deployment policy |
| DOC-NFR-005 | Auditability | 100% of published artifacts have manifest, checksums, revision IDs and approval state |
| DOC-NFR-006 | Accessibility | tagged heading levels, proper table headers, alt text for figures; automated checks when supported |
| DOC-NFR-007 | Reliability | atomic write + rollback to prior revision after failure |
| DOC-NFR-008 | Compatibility | Windows/Linux; test Office-compatible DOCX and common PDF viewers |
| DOC-NFR-009 | Scalability | 1,000 requirement IDs and 10,000 trace links in functional tests |
| DOC-NFR-010 | Privacy | configurable retention, restricted access, and safe redaction; do not copy client PII across workspaces |
| DOC-NFR-011 | Maintainability | JSON schema versioned, template tests, no hardcoded client organization identifiers |
| DOC-NFR-012 | Trace coverage | report coverage ratio for requirement->test and requirement->design; thresholds project-defined |

## 7. Mandatory metadata and document lifecycle
Metadata: `document_id`, `document_type`, `project_id`, `title`, `classification`, `language`, `revision`, `app_version`, `status`, `owner`, `reviewers`, `approvers`, `created_at`, `updated_at`, `effective_date`, `template_version`, `sources[]`, `change_reason`, `supersedes`, `hash`, `signoff_record[]`. Blank unknown fields remain `null`, no generated false names.
Statuses: DRAFT, IN_REVIEW, CHANGES_REQUESTED, APPROVED, RELEASED, SUPERSEDED, ARCHIVED. Approval records include identity, timestamp, decision, evidence link. No automatic approval.
Document IDs examples: `PROJ-SRS-001`, `PROJ-SDD-001`, `PROJ-UAT-001`; record IDs `FR-001`, `NFR-001`, `TC-001`, `BUG-001`, `INC-001`, `CR-001`, `ADR-001`.

## 8. Canonical architecture / pipeline
Sources (repo, user files, issue tracker, deployment manifest, meeting record) -> source collector + evidence labels -> import adapters -> normalized canonical JSON AST -> dependency/trace graph -> validate + diff + policy gate -> template renderers -> DOCX/PDF/XLSX/MD/JSON + signed-off manifest. External connectors OPTIONAL; no invented capability.
AST preserves `blocks[]` with `id`, `kind`, `title`, `body`, `tables`, `figures`, `source_refs`, `last_reviewed_at`; unsupported rich constructs stored as opaque references and flagged.

## 9. Synchronization triggers and authoritative sources
| Trigger | Main docs to inspect | Authority |
|---|---|---|
| Client requirement change | BRD/PRD, SRS, RTM, UAT, SDD | approved change request or stakeholder decision |
| Approved architecture decision | SDD, ADR, Juknis, Configuration | architecture decision record + reviewed implementation |
| API/database migration | SDD, API spec, ERD, Juknis, Config | schema/contract diff and deployment evidence |
| Defect opened/resolved | Bug log, test evidence, release note, CAPA | issue/ticket and verified regression |
| Security finding | Risk register, mitigation, release gate | scanner output + verified exception or fix |
| Release deployed | Change log, release notes, deployment record, config | CI artifact and release manager confirmation |
| Production incident | Incident report, RCA, corrective action | telemetry, timeline and human review |
| UAT completion | UAT report, RTM, BAST annex | actual execution evidence and authorized sign-off |
| Handover | Manuals, runbooks, asset list, BAST | accepted checklist and authorized representatives |

## 10. Document template / styling standard (custom original)
- Default: A4 portrait, margins 25mm left/right, 22mm top/bottom; landscape for wide RTM.
- Font: Aptos 11pt (fallback Calibri/Arial); institutional variant Times New Roman 12pt; body 1.15 line-height; justified optional, no forced full justification.
- Headings: H1 16pt bold; H2 13pt bold; H3 11pt bold; semantic structured numbering; avoid decorative heavy colors.
- Header: project / classification / doc ID. Footer: revision, page X of Y, status. Cover: logo optional, no fabricated logos, doc title, project ID, revision, date, owner.
- Tables: repeating header, alternating subtle neutral rows, descriptive captions, no split rows, fixed width for ID/status, high contrast.
- Include revision history, distribution list, TOC, abbreviations, references, approval page (empty until signed), appendices when relevant.
- XLSX: frozen top/header, filters, validations for status/severity, data dictionary and README tabs, protected calculated fields only if required, no macros.
- PDF: generated from canonical output, bookmarks and page numbering when tool supports them. Produce rendering QA report to flag overflow, pagination, missing glyphs.

## 11. CLI / Slash-command contract
`/shadow-doc create --type SRS --project PROJ --from ./sources --format docx,pdf,md --dry-run`
`/shadow-doc update --document PROJ-SRS-001 --change CR-002 --scope FR-014 --dry-run`
`/shadow-doc impact --change CR-002`
`/shadow-doc validate --project PROJ --strict`
`/shadow-doc diff --document PROJ-SDD-001 --from 1.1 --to 1.2`
`/shadow-doc export --document PROJ-UAT-001 --format xlsx,pdf`
`/shadow-doc package --project PROJ --stage handover`
Commands are *desired contract*, not claims of existing implementation. File writes require explicit permission for overwriting existing approved artifacts.

## 12. Data validation / fail-closed conditions
Block publish when required metadata invalid, duplicate IDs, broken critical trace links, unresolved critical validation, evidence missing for claimed PASS/APPROVED/DEPLOYED, unapproved change to controlled document, leaked secret, output render failure, or inconsistent revision. Nonblocking warnings: missing optional fields, low trace coverage thresholds, orphaned stale references, unsupported PDF formatting. Provide structured machine-readable issues with severity, location, remediation.

## 13. QA test scenarios / acceptance
- AT-01: Create 10 core docs from blank project, each with required section IDs; missing facts are placeholders.
- AT-02: Import legacy MD/JSON/DOCX; no unexplained content loss; unsupported elements identified.
- AT-03: Change FR-001; impact report links SDD, RTM, test cases, UAT; unrelated sections unchanged.
- AT-04: Approved SRS update cannot silently mutate approved revision; new DRAFT revision created.
- AT-05: Mismatched BUG status / test results must produce validation warning/blocker.
- AT-06: Secret string in config blocks publish; emitted files redact values.
- AT-07: Concurrent edits show conflict; no silent last-write-wins.
- AT-08: Render DOCX/PDF/XLSX; compare metadata, IDs, table values and revision; no orphan pages/overflow.
- AT-09: Repeated export produces same semantic payload; metadata that is intentionally volatile excluded from semantic checksum.
- AT-10: Cross-project source leak prevented.
- AT-11: BAST remains unsigned unless authorized evidence is explicitly supplied.
- AT-12: Migration from existing shadow-doc preserves backups and provides rollback plan.
- AT-13: Release manifest hashes match actual output files.
- AT-14: Failed atomic write restores prior version without corrupting artifact.
- AT-15: Mixed language output labels correct and no invented source references.

## 14. Implementation waves
P0 Wave 1: inventory existing shadow-doc, backward compatibility, canonical schema, templates, validation and MD export.
P0 Wave 2: DOCX/PDF/XLSX renderers + visual QA, revision records and preservation rules.
P0 Wave 3: trace graph, change impact, selective patch, approvals, manifest, release gates.
P1 Wave 4: additional project trackers/connectors, comments, scheduled document consistency audit, localization.
P1 Wave 5: resilience tests, scale benchmark, role permission tests, migration, docs, training, UAT and release.
No broad refactor without scope and tests. Current local skills must be inspected before implementing; avoid duplicate skill names or overwriting existing behavior.

## 15. Definition of Done
All templates have schema + sample data + render smoke tests; unit/integration/round-trip tests pass; real DOCX/XLSX/PDF artifacts visually inspected; end-to-end requirement change updates affected docs only; audit trail and approval state demonstrably correct; no leaked secrets; upgrade paths documented; handover includes README, template catalog, extension instructions, troubleshooting, and rollback plan.

## 16. Recommended implementation ownership
`shadow-doc` owns canonical AST, renderer, publication and registry. `shadow-discovery` owns requirement source; `shadow-architect` SDD/ADR; `shadow-uat` test acceptance; `shadow-release` release truth; `shadow-maintain` incident/bug truth; `shadow-handover` BAST/admin manuals. Monarch orchestrates, not duplicate validators. Use 3-tier activation and quality gates; no auto full suite for simple edits.

## 17. External references (framework inspiration; templates are original)
- ISO/IEC/IEEE 29148:2018 requirements engineering https://www.iso.org/standard/72089.html
- ISO/IEC/IEEE 42010:2022 architecture description https://www.iso.org/standard/74393.html
- ISO/IEC/IEEE 29119-3:2021 test documentation https://www.iso.org/standard/79429.html
- NIST SSDF SP 800-218 https://csrc.nist.gov/pubs/sp/800/218/final
- OWASP ASVS https://asvs.owasp.org/
The full proprietary standard texts are NOT copied, and alignment does not imply certified compliance.
