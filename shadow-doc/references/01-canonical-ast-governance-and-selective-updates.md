# 01. Generator-Agnostic Discovery, Canonical AST Governance & Selective Updates

## 1. Purpose & Activation Conditions
Use this playbook whenever creating, importing, updating, approving, or migrating formal SDLC, enterprise, or institutional deliverables (`.docx`, `.pdf`, `.xlsx`, `.csv`, `.md`, `.json`, `.zip`) via `/shadow-doc`. Its objective is to guarantee **zero direct binary editing**, **project-local generator respect**, **immutable approval governance**, **optimistic concurrency safety**, and **semantic conservation** across revisions.

Activate this playbook when:
- Modifying an existing `.docx`, `.xlsx`, or `.pdf` report in a brownfield repository.
- Performing targeted section updates (`scope_id`) on an approved or shared Canonical JSON AST v2.0 document.
- Auditing whether a repository already owns a native document generator (`doc_orchestrator.py`) before introducing the global `shadow-doc` engine.

## 2. Prerequisites
- Target workspace inspected via `doc_orchestrator.py discover` / `resolve` (read-only `L0`).
- Knowledge of the owning domain skill supplying technical truth (`/shadow-discovery`, `/shadow-architect`, `/shadow-uat`, `/shadow-maintain`, `/shadow-handover`) — `/shadow-doc` governs structure, traceability, validation, and rendering rather than inventing technical facts.
- Reference schema [`HYBRID-JSON-MD-SCHEMA.md`](HYBRID-JSON-MD-SCHEMA.md) and [`../schemas/canonical-document.schema.json`](../schemas/canonical-document.schema.json).

## 3. Technical Principles & Constraints
1. **Never Edit Binary Outputs Directly (`.docx`, `.xlsx`, `.pdf`)**:
   - Trace every requested binary deliverable back to its maintained source (`.json`, `.md`, `.yaml`, or project template) and its owning generator command. If two outputs in the same repo are owned by different generators, record each mapping explicitly, edit ONLY the owning source, and regenerate through that generator.
2. **Generator-Agnostic Precedence (`SA-DOC-ENGINE-001`)**:
   - Before forcing Canonical JSON AST v2.0 onto a repository, follow strict discovery precedence:
     `Explicit User Selection -> Project-Local Discovery -> Project Config (.shadow/document-engine.json) -> Global Engine Fallback (shadow-doc) -> User Decision Gate (Options A/B/C/D)`.
   - Classify discovered project generators (`COMPATIBLE | PARTIALLY_COMPATIBLE | INCOMPATIBLE | UNKNOWN`). Reuse compatible generators untouched; bridge partial gaps with `MarkdownCompatibilityAdapter` / `domain_adapters.py` rather than replacing working pipelines silently.
3. **Immutable `APPROVED`/`RELEASED` Protection & Separation of Duties (`DOC-FR-010`, `DOC-FR-011`)**:
   - Approved/released documents are strictly immutable in-place. Running `doc_scaffold.py update` on an `APPROVED` document automatically forks a new `DRAFT` revision (e.g., `1.1-DRAFT`) with `supersedes` linked to the prior approved revision.
   - `owner != approver` is hard-enforced (`approve` rejects self-approval), and `HANDOVER` / `BAST` artifacts cannot reach `APPROVED`/`RELEASED` without a signed `evidence_ref`.
4. **Selective `scope_id` Patching & Optimistic Concurrency (`DOC-FR-007`)**:
   - Patch ONLY the targeted `scope_id` (e.g., `FR-001`) without rewriting unrelated blocks, recording `before_hash` and `after_hash` in `history[]`. Concurrent mutations carrying a stale `expected_hash` fail closed (`CONCURRENCY_CONFLICT`).
5. **Semantic Conservation & Output Path Safety**:
   - Before delivery, compare required identifiers, owners, exceptions, versions, and table columns in the rendered artifact against its maintained source (`test_semantic_conservation.py` — renaming a title is allowed, silently dropping an `exception_notes` column is a `SEMANTIC_REGRESSION`!).
   - `export` blocks path traversal and ancestor symlinks (`--allowed-root`) and enforces `execution_approval_gate.py` so `--overwrite` fails closed unless paired with a valid scoped `--approval-file`.
6. **100% Legacy v1.0 Backward Compatibility**:
   - Preserve support for legacy v1.0 `bagian -> subbagian -> blok` JSON files (`check-readiness`) and migrate losslessly via `migrate-v1` (which automatically retains a `.v1.bak.json` backup and `legacy_v1_bagian`).

## 4. Architecture & Implementation
### Generator Discovery & Controlled Update Workflow (`PowerShell`)
```powershell
# Set $ShadowDocRoot to the directory containing the installed shadow-doc SKILL.md
# 1. Discover any project-local document generator first (L0 read-only)
python "$ShadowDocRoot/scripts/doc_orchestrator.py" discover --repo .

# 2. Selectively patch one block with optimistic concurrency check (auto-forks if APPROVED)
python "$ShadowDocRoot/scripts/doc_scaffold.py" update `
  --doc docs/SRS.json --scope-id FR-001 `
  --content "Sistem wajib mendukung OAuth2/OIDC dengan FIDO2 Passkey." `
  --author "Security Architect" --change-ref CR-001

# 3. Trace cross-document change impact before approval
python "$ShadowDocRoot/scripts/doc_scaffold.py" impact `
  --doc docs/SRS.json docs/RTM.json --changed-id FR-001

# 4. Controlled approval (enforces owner != actor & evidence_ref)
python "$ShadowDocRoot/scripts/doc_scaffold.py" approve `
  --doc docs/SRS.json --status APPROVED --actor "VP Engineering" `
  --role "Approver" --evidence-ref "MINUTES-2026-11-10"
```

### Strict TypeScript Semantic Conservation & Governance Guard
```typescript
export type DocStatus = 'DRAFT' | 'IN_REVIEW' | 'APPROVED' | 'RELEASED';

export interface ApprovalTransitionRequest {
  readonly docType: string;
  readonly owner: string;
  readonly actor: string;
  readonly targetStatus: DocStatus;
  readonly evidenceRef: string | null;
}

export function validateApprovalTransition(
  req: ApprovalTransitionRequest,
): { readonly allowed: boolean; readonly errorCode: string | null } {
  const requiresGate =
    req.targetStatus === 'APPROVED' || req.targetStatus === 'RELEASED';
  if (!requiresGate) {
    return { allowed: true, errorCode: null };
  }
  if (req.owner.trim().toLowerCase() === req.actor.trim().toLowerCase()) {
    return { allowed: false, errorCode: 'SELF_APPROVAL_FORBIDDEN' };
  }
  const formalHandover =
    req.docType === 'HANDOVER' || req.docType === 'BAST';
  if (formalHandover && (req.evidenceRef === null || req.evidenceRef.trim() === '')) {
    return { allowed: false, errorCode: 'MISSING_SIGNED_EVIDENCE_REF' };
  }
  return { allowed: true, errorCode: null };
}
```

## 5. Platform / Vendor Variations
- **Repositories With Existing Docs Generators (Pandoc / LaTeX / Quarto / Python-docx custom scripts)**: Detect via `doc_orchestrator.py discover`; if classified `COMPATIBLE`, edit the project's native Markdown/YAML source and run its verified build script instead of imposing a second competing pipeline.
- **Greenfield Enterprise / Government SDLC Suites (Indonesia)**: Use `shadow-doc`'s 20 standardized templates (`templates/01..20`, `lang=id-ID`, `style=institutional` for government `Times New Roman 12pt` or `corporate` for `Calibri 11pt`) backed by Canonical JSON AST v2.0.
- **Legacy Shadow-Doc v1.0 Repos**: Keep existing v1 JSON working seamlessly or upgrade deterministically via `migrate-v1` without data loss.

## 6. Decision Matrix & Trade-Offs
| Scenario | Action | Rationale |
| :--- | :--- | :--- |
| **Repo has compatible Pandoc/custom `.docx` script** | Edit native `.md` source + run existing repo generator | Zero competing pipelines; preserves house styling |
| **Updating 1 requirement inside an `APPROVED` SRS JSON** | Run `doc_scaffold.py update --scope-id FR-001` | Auto-forks `1.1-DRAFT`, preserves `before_hash`/`after_hash`, never mutates approved baseline in place |
| **Requested to "just open `Final_SRS.docx` and change paragraph 4"** | **Refuse direct binary edit** -> locate owning `.json`/`.md` source & regenerate | Prevents permanent source-to-output drift |

## 7. Real Production Scenario
**Context:** A vendor team manually opened `BAST_v1.0.docx` in Word to fix a version typo and accidentally deleted the `exception_notes` column from the UAT Sign-Off table. When the next sprint regenerated the document from Markdown, the typo returned and nobody noticed the lost waiver notes until final client audit.
**Fix:** Adopting `doc_scaffold.py` selective `scope_id` updates + `verify_semantic_conservation` (blocking silent dropped columns while permitting title updates) and banning direct `.docx` edits eliminated source/binary drift completely.

## 8. Failure Modes & Edge Cases
- **WRONG (Directly mutating `.docx` / `.xlsx` binaries or overwriting `APPROVED` documents in-place):** Breaks audit traceability, erases `history[]` hashes, and allows self-approval (`owner == approver`).
  **RIGHT:** Edit the verified maintained source, let `doc_scaffold.py update` auto-fork a new `DRAFT` revision from `APPROVED`, enforce `owner != approver`, and regenerate cleanly.
- **WRONG (Forcing JSON AST v2.0 onto a repo that already runs a working Markdown/Pandoc build pipeline):** Creates duplicate conflicting document sources.
  **RIGHT:** Run `doc_orchestrator.py discover` first and reuse compatible project-local generators cleanly.

## 9. Testing & Verification
- Run `python shadow-doc/scripts/doc_scaffold.py --selftest` (v1 backward-compat self-test).
- Run `python -m unittest discover -s shadow-doc/tests -v` (`test_semantic_conservation.py` + `test_reference_archive.py`).
- Before delivering regenerated binaries, confirm every required ID, owner, exception note, version, and table column from the source appears intact in the rendered output.

## 10. Operational Considerations
- Always run `doc_scaffold.py impact --doc <docs...> --changed-id <FR-ID>` when modifying an approved requirement so dependent `SDD`, `RTM`, `TEST_PLAN`, and `UAT` artifacts stay synchronized.
- Keep `.build-manifest.json` outputs alongside packaged handover deliverables to prove exact source-to-artifact provenance.

## 11. Authoritative References
- **ISO/IEC/IEEE 29148:2018**, **42010:2022**, **12207:2017**, **26514:2022** — Normative SDLC document structure & configuration management standards.
- **Shadow Doc Internal Specs** — [`HYBRID-JSON-MD-SCHEMA.md`](HYBRID-JSON-MD-SCHEMA.md), [`../TEMPLATE_CATALOG.md`](../TEMPLATE_CATALOG.md), and [`../requirements/SHADOW_DOC_V2_PRD_SRS.md`](../requirements/SHADOW_DOC_V2_PRD_SRS.md).

## 12. Limitations & When NOT to Use
- **Do NOT use** `/shadow-doc` to invent missing technical architecture, requirements, or security findings — gather verified facts from the owning domain skill (`/shadow-discovery`, `/shadow-architect`, `/shadow-sec`, `/shadow-uat`) first.
- **Do NOT use** `/shadow-doc` for AI session memory handoffs — use `/handoff` (`shadow_handoff` MCP).
