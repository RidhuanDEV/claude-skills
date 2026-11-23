# 02. Citation Verification, 7-Point Reference Safety Gate & Multi-Format Export QA

## 1. Purpose & Activation Conditions
Use this playbook when validating evidence-backed claims inside formal documents (`validate --strict`), citing industry standards or scholarly papers, downloading and quarantining external reference files (`reference_verifier.py`), redacting leaked secrets / cross-project `forbidden_terms`, and executing multi-format visual/structural QA across `.docx`, `.pdf`, `.xlsx`, `.csv`, and `.zip` deliverables.

Activate this playbook when:
- Running strict pre-release validation (`doc_scaffold.py validate --strict`) on any SDLC or institutional deliverable.
- Downloading external PDFs, standards, or research papers into `docs/references/` and verifying file safety.
- Packaging final client deliverables (`doc_scaffold.py export` / `package`) requiring secret redaction, cross-project term isolation, and atomic file integrity.

## 2. Prerequisites
- Canonical JSON AST v2.0 document (or verified project source) ready for citation, secret, and export checks.
- Installed scripts `shadow-doc/scripts/doc_scaffold.py` and `shadow-doc/scripts/reference_verifier.py` (Python 3 stdlib + optional `python-docx` / `openpyxl` / `fpdf2` for binary exports).
- Policy anchor: `shadow-monarch/reference/RESEARCH-SOURCE-POLICY.md`.

## 3. Technical Principles & Constraints
1. **Zero Fabricated Facts & Evidence-Backed Claims (`DOC-FR-012`, `DOC-FR-020`, `AT-09`)**:
   - NEVER fabricate dates, ticket IDs, metrics, stakeholder names, test results, or deployment topologies. Unknown facts MUST remain explicit placeholders (`[ISI ...]`, `[TBD]`, `UNVERIFIED`).
   - Any block asserting `PASS`, `APPROVED`, `DEPLOYED`, or `CLOSED` MUST cite a verified `source_refs` entry. `validate --strict` fails closed if unresolved placeholders or unreferenced verification claims exist.
2. **Normative Standards First & Strict `arXiv` Preprint Rules**:
   - Anchor SDLC documents to authoritative international/national standards first (`ISO/IEC/IEEE 29148:2018`, `42010:2022`, `29119`, `25010`, `NIST SSDF SP 800-218`, `OWASP ASVS 5.0.0`, `NIST SP 800-61`, `ISO/IEC/IEEE 14764`, `UU PDP No. 27/2022`) and version-matched official framework docs (`/context7`).
   - For empirical scholarly backing, verify DOI/URL, publisher/venue, year, and peer-review status (`IEEE Xplore`, `ACM Digital Library`, `SpringerLink`, `ScienceDirect`). NEVER default to `arXiv` for software engineering standards; any unreviewed `arXiv` preprint MUST be tagged `source_type: "PREPRINT"` (`peer_reviewed: false`, `[PREPRINT]`).
3. **Mandatory Local Download & 7-Point File Safety Gate (`reference_verifier.py`)**:
   - Download publicly accessible references into `docs/references/` tracked by `references_manifest.json` (with SHA-256 checksums) and scan every file with `reference_verifier.py scan docs/references --quarantine-delete`:
     1. Extension allowlist check (blocks `.exe`, `.bat`, `.ps1`, `.js`, `.vbs`, `.docm`, `.xlsm`, `.scr`, etc.).
     2. Double-extension spoofing check (blocks `paper.pdf.exe` or hidden executable suffixes).
     3. Magic-byte verification (`%PDF-` required for `.pdf`; blocks `MZ` PE / `ELF` / Mach-O binaries disguised as `.pdf`).
     4. PDF active-content exploit scan (blocks `/JavaScript`, `/JS`, `/Launch`, `/OpenAction` malicious payloads).
     5. HTML/SVG `<script>` / `onerror=` injection check.
     6. Size & path-traversal containment check (no escaping `docs/references/`).
     7. SHA-256 manifest registration + **automatic quarantine deletion** of unsafe files from the local PC!
4. **Secret Scanning, Cross-Project Isolation & Atomic Export (`AT-06`, `AT-10`, `AT-14`)**:
   - Automatically redact leaked credentials (`[REDACTED_SECRET]`) before any export leaves the workspace.
   - Reject any document containing cross-project `forbidden_terms` (prevents accidentally copying Client A's name or internal codename into Client B's proposal/BAST!).
   - Write all rendered artifacts atomically via `.tmp` + `.bak` rollback so interrupted exports never corrupt prior outputs.
5. **Cross-Format Visual & Structural QA**:
   - **UTF-8 everywhere on Windows** (`encoding="utf-8"`).
   - **DOCX**: A4 portrait/landscape (`RTM`), running headers/footers, native Word `TOC \o "1-3"` field (remind user `Ctrl+A` then `F9` in Word to refresh dynamic page numbers), repeating headers (`w:tblHeader`), `w:cantSplit`, heading `keep_with_next`.
   - **XLSX**: Standardized 4 sheets (`README_Metadata`, `Register_Data` with frozen header `A2` + filter + status dropdown, `Traceability_Links`, `Data_Dictionary`).
   - **PDF**: Native offline rendering with running headers, page `X/{nb}` footers, section bookmarks, and wrapped tables.
   - **ZIP Handover Bundle**: Deterministic archive + `manifest.json` with per-file SHA-256 digests.

## 4. Architecture & Implementation
### End-to-End Citation Safety & Strict Export Pipeline (`PowerShell`)
```powershell
# 1. Fetch external reference locally & enforce 7-Point File Safety + SHA-256 manifest
python "$ShadowDocRoot/scripts/reference_verifier.py" fetch `
  --url "https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-218.pdf" `
  --dest-dir docs/references --title "NIST SSDF SP 800-218" `
  --venue "NIST" --year "2022" --doi "10.6028/NIST.SP.800-218"

# 2. Re-scan local references directory and auto-delete any disguised/malicious file
python "$ShadowDocRoot/scripts/reference_verifier.py" scan docs/references --quarantine-delete

# 3. Strict pre-release validation (blocks [TBD], unreferenced PASS claims, secrets, forbidden_terms)
python "$ShadowDocRoot/scripts/doc_scaffold.py" validate --doc docs/SRS.json --strict

# 4. Multi-format export (DOCX, PDF, XLSX, CSV, MD) + handover ZIP with SHA-256 manifest
python "$ShadowDocRoot/scripts/doc_scaffold.py" export --doc docs/SRS.json --format all --out-dir docs/output
python "$ShadowDocRoot/scripts/doc_scaffold.py" package `
  --source-dir docs/output --project-id PRJ-2026 --stage handover --out docs/Handover_Bundle.zip
```

### Strict TypeScript Claim-Provenance & Preprint Policy Guard
```typescript
export type SourceType = 'NORMATIVE_STANDARD' | 'PEER_REVIEWED' | 'OFFICIAL_DOCS' | 'PREPRINT';

export interface CitationEntry {
  readonly sourceId: string;
  readonly title: string;
  readonly sourceType: SourceType;
  readonly peerReviewed: boolean;
  readonly sha256: string | null;
}

export interface DocumentBlock {
  readonly id: string;
  readonly statusClaim: 'PASS' | 'APPROVED' | 'DEPLOYED' | 'CLOSED' | 'DRAFT';
  readonly body: string;
  readonly sourceRefs: readonly string[];
}

export function auditStrictDocumentClaims(
  blocks: readonly DocumentBlock[],
  citations: ReadonlyMap<string, CitationEntry>,
): readonly string[] {
  const errors: string[] = [];
  for (const block of blocks) {
    if (block.body.includes('[TBD]') || block.body.includes('[ISI ')) {
      errors.push(`${block.id}: unresolved placeholder blocks --strict release.`);
    }
    if (block.statusClaim !== 'DRAFT' && block.sourceRefs.length === 0) {
      errors.push(`${block.id}: '${block.statusClaim}' claim missing verified source_refs.`);
    }
    for (const refId of block.sourceRefs) {
      const citation = citations.get(refId);
      if (citation === undefined) {
        errors.push(`${block.id}: dangling source_ref '${refId}'.`);
      } else if (citation.sourceType === 'PREPRINT' && citation.peerReviewed) {
        errors.push(`${refId}: PREPRINT cannot be marked peerReviewed=true without verified venue DOI.`);
      }
    }
  }
  return errors;
}
```

## 5. Platform / Vendor Variations
- **Windows Corporate Environments (PowerShell + Word)**: Always force explicit UTF-8 file I/O to avoid `cp1252` Mojibake in Bahasa Indonesia/Unicode tables, and advise reviewers to press `Ctrl+A` then `F9` in Microsoft Word to populate dynamic `TOC` page numbers.
- **Air-Gapped / Restricted Networks**: When external downloads cannot run live, record `download_status: "OFFLINE_BLOCKED"` honestly in `references_manifest.json` while still scanning any manually supplied local PDFs with `reference_verifier.py scan --quarantine-delete`.

## 6. Decision Matrix & Trade-Offs
| Verification Gate | Draft Stage (`validate`) | Release Stage (`validate --strict`) |
| :--- | :--- | :--- |
| **Unresolved `[TBD]` / `[ISI ...]` placeholders** | Allowed (warning) — prevents hallucinating missing facts | **BLOCKED (FAIL)** — must resolve or explicitly sign off exceptions |
| **`PASS`/`APPROVED` claim without `source_refs`** | Warning | **BLOCKED (FAIL)** |
| **Leaked Secret / Cross-Project `forbidden_terms`** | **BLOCKED / REDACTED** | **BLOCKED / REDACTED** |
| **Disguised `.pdf` (`MZ` header or `/JavaScript`)** | **AUTO-DELETED (Quarantine)** | **AUTO-DELETED (Quarantine)** |

## 7. Real Production Scenario
**Context:** While assembling an enterprise security assessment report, a team reused a previous client's SRS template and downloaded a third-party "whitepaper.pdf" from an unverified blog mirror.
**Blocked Disasters:** Running `doc_scaffold.py validate --strict` caught two lingering mentions of the previous client's name via `forbidden_terms` AND an accidentally pasted staging Bearer token (`[REDACTED_SECRET]`), while `reference_verifier.py scan --quarantine-delete` detected an embedded `/JavaScript` `/OpenAction` payload inside the downloaded PDF and automatically removed the unsafe file before anyone opened it locally.

## 8. Failure Modes & Edge Cases
- **WRONG (Filling missing stakeholder dates/metrics with plausible guesses to pass `--strict`):** Replacing `[ISI TANGGAL UAT]` with an invented date `"2026-11-15"` or writing `"p95 = 120ms (PASS)"` without an executed benchmark log.
  **RIGHT:** Keep unknown facts as explicit `[TBD]` / `UNVERIFIED` placeholders until real verified evidence exists, then attach the actual `source_refs` entry.
- **WRONG (Citing unreviewed `arXiv` preprints as authoritative compliance standards or skipping local file safety scans):** Treating an unreviewed blog/preprint as equivalent to `NIST SP 800-218` or saving uninspected internet PDFs into the repo.
  **RIGHT:** Cite normative standards first, tag unreviewed preprints `[PREPRINT]` (`peer_reviewed: false`), and run `reference_verifier.py scan docs/references --quarantine-delete` on every local reference file.

## 9. Testing & Verification
- Run `python shadow-doc/scripts/reference_verifier.py --self-test` to confirm 7-point safety probes (`MZ` disguised as `.pdf`, `/JavaScript` PDF exploit, `<script>` HTML injection, double extension, clean PDF precision).
- Run `python -m unittest discover -s shadow-doc/tests -v` (`test_reference_archive.py` + `test_semantic_conservation.py`).
- Run `python shadow-doc/scripts/doc_scaffold.py --selftest` and verify zero secret/forbidden-term leaks before handing off exported artifacts.

## 10. Operational Considerations
- Commit `docs/references/references_manifest.json` alongside project deliverables (and exclude oversized binary PDFs if repo policy restricts them, while still retaining SHA-256 provenance and local scan proof).
- Always run `validate --strict` after the final source edit before running `export` and `package`.

## 11. Authoritative References
- **Shadow Monarch Policy** — `shadow-monarch/reference/RESEARCH-SOURCE-POLICY.md` (source hierarchy & 7-point file safety).
- **NIST SSDF SP 800-218** — *Secure Software Development Framework* (`https://csrc.nist.gov/publications/detail/sp/800-218/final`).
- **ISO/IEC/IEEE 29148:2018**, **29119-3:2021**, **25010:2023**, and **OWASP ASVS 5.0.0**.

## 12. Limitations & When NOT to Use
- **Do NOT use** `reference_verifier.py` as a full enterprise antivirus replacement on untrusted arbitrary binaries — it enforces deterministic document-format safety checks for reference archives (`docs/references/`).
- **Do NOT use** `doc_scaffold.py export` to invent missing source artifacts; generate technical test/security evidence via `/shadow-test`, `/shadow-sec`, and `/shadow-uat` first.
