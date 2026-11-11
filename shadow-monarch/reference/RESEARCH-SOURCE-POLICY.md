# Research & Standards Source Routing Policy — Shadow Army

## 1. Core Doctrine: Task-Based Source Routing (Not Blind `arXiv` Lookup)

In enterprise and government software engineering, **international standards (`ISO/IEC/IEEE`, `NIST`, `OWASP`), official version-matched framework documentation (`Context7`), and peer-reviewed publications (`IEEE Xplore`, `ACM Digital Library`, `SpringerLink`, `ScienceDirect`)** are the primary sources of truth.

- **`arXiv` is a Preprint Repository**: Articles on `arXiv` have **not** necessarily undergone formal peer review. Never use `arXiv` as the default search source for Software Engineering, SDLC documentation, architecture, testing, or security compliance.
- **Normative Standards First for `/shadow-doc`**: Every SDLC document (`SRS`, `SDD`, `RTM`, `TEST_PLAN`, `UAT`, `SECURITY_RISK`, `HANDOVER`, `DEPLOYMENT`, etc.) must anchor its structure and quality gates to recognized industry standards. Academic papers are used as **supporting evidence** only when a specific algorithm, methodology, or architectural trade-off requires empirical research backing.

---

## 2. Master Source Comparison & Classification Matrix

| Source / Authority | Source Type | Peer-Reviewed / Normative | Primary Engineering Use Case |
| :--- | :--- | :--- | :--- |
| **ISO / IEC / IEEE Standards** | `STANDARD` | Yes (Normative Consensus) | SDLC processes (`12207`), Requirements/`SRS` (`29148`), Architecture/`SDD` (`42010`), Testing/`UAT`/`RTM` (`29119`), Quality (`25010`). |
| **NIST (CSRC)** | `STANDARD` | Yes (Normative Gov/Sec) | Secure Software Development (`SSDF SP 800-218`), Security Controls (`SP 800-53`), Incident Response (`SP 800-61`), Risk (`CSF 2.0`). |
| **OWASP Foundation** | `STANDARD` | Yes (Industry Standard) | Application Security Verification Standard (`ASVS 5.0`), API Security, Top 10 Web/Mobile/LLM Security, Testing Guide (`WSTG`). |
| **Context7 / Official Vendor Docs** | `OFFICIAL_DOCS` | Yes (Canonical Maintainer) | Exact version-matched framework, library, SDK, database, and runtime APIs (`/context7` MCP, IETF RFCs, W3C, OpenAPI 3.1). |
| **IEEE Xplore** | `PEER_REVIEWED` | Yes (Peer-Reviewed) | Empirical software engineering, distributed systems, enterprise architecture, information systems, dependability. |
| **ACM Digital Library** | `PEER_REVIEWED` | Yes (Peer-Reviewed) | Computer science, programming languages, algorithms, software engineering (ICSE, FSE, OSDI, SOSP, SIGMOD). |
| **SpringerLink** | `PEER_REVIEWED` | Yes (Peer-Reviewed) | Academic journals (`Empirical Software Engineering`), LNCS conference proceedings, and foundational textbooks. |
| **ScienceDirect (Elsevier)** | `PEER_REVIEWED` | Yes (Peer-Reviewed) | Information systems, enterprise technology adoption, software project management (`Journal of Systems and Software`, `IST`). |
| **Semantic Scholar / OpenAlex / Google Scholar** | `INDEX_ENGINE` | Mixed (Verify Venue & DOI) | Cross-publisher literature discovery, citation graph traversal, impact tracking, and DOI resolution. |
| **arXiv** | `PREPRINT` | **No** (Preprint unless published) | Cutting-edge AI/ML/LLM architectures, rag/agent benchmarks, and emerging preprints. Must be labeled `[PREPRINT]` unless a peer-reviewed DOI exists. |

---

## 3. Task-to-Source Routing Table

Whenever the Shadow Army researches, designs, implements, audits, or documents a system, route lookups strictly by task domain:

| Engineering Task / Artifact | 1st Priority (Normative / Primary) | 2nd Priority (Empirical / Secondary) | 3rd Priority (Supplementary) |
| :--- | :--- | :--- | :--- |
| **SRS / PRD / BRD (`/shadow-discovery`, `/shadow-doc`)** | **ISO/IEC/IEEE 29148:2018**, Domain Regulations (UU PDP, SNAP BI, SatuSehat) | IEEE Xplore / ACM DL (Requirements Engineering), ScienceDirect | Project KAK/TOR & Stakeholder Minutes |
| **SDD / ADR / System Design (`/shadow-architect`, `/shadow-doc`)** | **ISO/IEC/IEEE 42010:2022**, **ISO/IEC 25010**, IETF RFCs | IEEE Xplore, ACM DL, SpringerLink | Official Cloud/DB Architecture Guides |
| **Testing, RTM & UAT (`/shadow-test`, `/shadow-uat`, `/shadow-doc`)** | **ISO/IEC/IEEE 29119-1..5**, **ISO/IEC 25010** | IEEE Xplore / ACM DL (Software Testing & Verification) | Official Test Runner Docs via `/context7` |
| **AppSec, Threat Model & Sec Audit (`/shadow-sec`, `/shadow-auth`)** | **NIST SSDF (SP 800-218)**, **OWASP ASVS 5.0.0**, **NIST SP 800-53** | IEEE S&P, ACM CCS, USENIX Security | CVE / NVD Advisories & Vendor Security Bulletins |
| **Framework & Code Implementation (`shadow-monarch`)** | **Official Docs via `/context7` MCP** (matched to `package.json`/`go.mod`/`pyproject.toml`) | Official GitHub Repo / Release Notes / Migration Guides | RFCs & W3C / WHATWG Specifications |
| **Ops, Incident RCA & Handover (`/shadow-ops`, `/shadow-maintain`, `/shadow-handover`)** | **ISO/IEC 20000-1**, **NIST SP 800-61r2**, **IEEE 1063** (User Docs), **ISO/IEC/IEEE 14764** (Maintenance) | local OWASP/H5BP knowledge base, SRE Books | Vendor Operator Runbooks |
| **AI / ML / LLM Engineering (`sub-RAG`, `sub-LLM-FINETUNING`)** | **IEEE Xplore**, **ACM DL**, **Springer**, NeurIPS/ICML/ICLR/ACL Proceedings | **Semantic Scholar / OpenAlex** (citation-filtered) | **`arXiv` Preprints** (explicitly marked `PREPRINT`) |

---

## 4. Mandatory 8-Point Source Verification, Local Download & File Safety Protocol

Before citing any external standard, documentation, or research paper in code comments, ADRs, or `/shadow-doc` artifacts, verify, download locally, and safety-check:

1. **Source Category (`source_type`)**: Classify as `STANDARD`, `OFFICIAL_DOCS`, `PEER_REVIEWED`, `REGULATION`, `PROJECT_ARTIFACT`, or `PREPRINT`.
2. **Publication Year & Version (`version_or_year`)**: Verify the exact standard edition (e.g., `ISO/IEC/IEEE 29148:2018`, `OWASP ASVS 5.0.0`) or library version (`Next.js 15.x`). Reject obsolete editions when a current standard applies.
3. **Persistent Identifier (`doi_or_url`)**: Record the official DOI (`10.1109/...`, `10.1145/...`), ISO/NIST standard number, or canonical documentation URL.
4. **Peer-Review & Normative Status (`peer_reviewed`)**: Explicitly distinguish peer-reviewed journal/conference papers and ratified standards (`peer_reviewed: true`) from unreviewed preprints (`peer_reviewed: false`). Every `arXiv` preprint without a verified journal/conference DOI must carry the `[PREPRINT]` badge.
5. **Publisher & Venue Credibility (`standard_or_venue`)**: Verify the publisher (`ISO`, `IEEE`, `ACM`, `NIST`, `OWASP`, `Springer`, `Elsevier`). Do not treat anonymous blogs or unverified preprints as normative standards.
6. **Traceable Citation in AST (`sources[]` & `source_refs[]`)**: Every normative rule or empirical claim in `/shadow-doc` must link its block `source_refs` to an entry in `root.sources[]`.
7. **Mandatory Local Download & Offline Archival (`docs/references/`)**:
   - Whenever a cited reference (open-access paper, public standard PDF/spec from NIST/OWASP/IETF/W3C, or technical bulletin) is publicly downloadable, download a local copy into `<project>/docs/references/` using `shadow-doc/scripts/reference_verifier.py fetch` and record its `sha256`, `doi_or_url`, `venue`, `peer_reviewed`, and `citation_badge` in `docs/references/references_manifest.json`.
8. **Mandatory 7-Point File Safety Re-Check (`reference_verifier.py` — Zero Dangerous Files on Local PC)**:
   - Every downloaded or imported reference file MUST pass `python "shadow-doc/scripts/reference_verifier.py" scan <path> --quarantine-delete` before being kept or opened:
     1. **Blocked Executable/Macro Extensions**: Rejects `.exe`, `.dll`, `.bat`, `.cmd`, `.ps1`, `.vbs`, `.js`, `.scr`, `.msi`, `.jar`, `.docm`, `.xlsm`, `.pptm`, `.lnk`, `.iso`.
     2. **Double-Extension Spoof Detection**: Blocks disguised filenames such as `paper.pdf.exe` or `standard.pdf.ps1`.
     3. **Magic-Byte Header Verification**: Verifies `%PDF-` header on `.pdf` files and blocks Windows PE (`MZ`), Linux `ELF`, Mach-O, or ZIP/Archive (`PK`) binaries masquerading as PDFs or text files.
     4. **PDF Active-Content / Exploit Scan**: Rejects PDFs containing `/JavaScript`, `/JS`, `/Launch`, `/EmbeddedFiles`, `/RichMedia`, `/XFA`, or `/SubmitForm` dictionary actions.
     5. **Text/HTML Script Injection Scan**: Rejects `.html`/`.md`/`.txt` references containing active `<script>`, `<iframe>`, `<object>`, `<embed>`, inline `onload=`/`onerror=`, or `javascript:` URIs.
     6. **File Size Sanity Check**: Rejects 0-byte files or >100 MB archive bombs.
     7. **Automatic Quarantine Deletion**: Any file failing safety verification is immediately deleted from disk (`DELETED_UNSAFE_FILE`) so dangerous files never remain on the Monarch's PC.
