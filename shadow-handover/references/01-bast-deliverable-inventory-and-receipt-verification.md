# 01. BAST Deliverable Inventory, Immutable Artifact Provenance & Receipt Verification

## 1. Purpose & Activation Conditions
Use this playbook when preparing formal client delivery and **Berita Acara Serah Terima (BAST)** packages so the client receives an auditable, reproducible software release rather than a loose zip file. Every handed-over deliverable MUST be bound to an immutable release commit, cryptographic artifact digest (`contract_sha256`), SBOM/license manifest, explicit acceptance criteria, and verified recipient authority.

Activate this playbook when:
- Assembling the 7 mandatory Gate 8 client handover deliverables (BAST, Source/SBOM Inventory, Vault Manifest, Admin Runbook, User Manual, ToT Package, Warranty Boundary).
- Running `shadow-handover/scripts/check_receipt.py` to validate a release artifact against its signed receipt JSON.
- Tracking partial/staged handovers where specific items remain pending due to missing signatures, digest mismatches, or unverified vault access.

## 2. Prerequisites
- Signed Staging UAT completion (`Berita Acara UAT` from `/shadow-uat`) and production/release candidate artifact digest (`/shadow-release`).
- Verified CycloneDX/SPDX SBOM and license audit from `/shadow-supplychain`, DB schemas/seeds from `/shadow-db` & `/shadow-data`, and OpenAPI/collection specs from `/shadow-api`.
- Single Document Engine boundary (`SA-DOC-ENGINE-001`): resolve project-local generator first via `shadow-doc/scripts/doc_orchestrator.py resolve --repo . --outputs docx,pdf,md`.

## 3. Technical Principles & Constraints
1. **Strict Distinction: `/shadow-handover` vs `/handoff`**:
   - `/shadow-handover` executes formal **client system & BAST delivery**.
   - `/handoff` (`shadow_handoff` MCP) saves/loads **AI coding session memory**. Never confuse the two.
2. **Immutable Provenance & Per-Item Completeness (`test_partial_handover_cutover.py`)**:
   - Identify every contracted release strictly by immutable Git commit SHA and binary/archive SHA-256 digest (`contract_sha256`).
   - Record agreed scope, warranty owner, sender, recipient, acceptance criteria, and explicit exceptions **per deliverable item**. A missing signature, mismatched digest, or inaccessible vault secret leaves that specific item `PENDING` — NEVER stamp a whole BAST `COMPLETE` when an item is unverified!
   - Creating release Git tags or pushing tags requires explicit `L4` release authorization (`/shadow-release`).
3. **Human Verification Boundary of `check_receipt.py`**:
   - `python shadow-handover/scripts/check_receipt.py ARTIFACT RECEIPT.json` verifies digest equality and mandatory reference field presence (`release`, `contract_ref`, `sender`, `recipient`, `criteria`, `warranty_owner`, `contract_sha256`, `signed_receipt_ref`, `operator_demo_ref`, `access_receipt_ref`).
   - A human reviewer MUST still open the referenced files, confirm the signatory's legal authority, and verify the actual operator walkthrough outcome.
4. **Zero Bespoke Document Renderers**:
   - Never embed custom `.docx`/`.pdf` exporters inside handover scripts; route formal `HANDOVER`/`BAST` documents exclusively through `shadow-doc/scripts/doc_orchestrator.py` (`domain_adapters.py::adapt_handover_payload`) so `owner != approver` and `evidence_ref` gates stay enforced.

## 4. Architecture & Implementation
### Complete Contracted Handover Receipt JSON (`scripts/check_receipt.py`)
```json
{
  "release": "v1.4.0",
  "contract_ref": "SPK-2026-089/IT-GOV",
  "sender": "vendor-delivery-lead@example.org",
  "recipient": "client-it-head@example.go.id",
  "criteria": "All P0/P1 UAT scenarios passed; backup restore drill RTO=18m verified by client operator.",
  "warranty_owner": "vendor-support-l2@example.org (Harwat 90d)",
  "contract_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "signed_receipt_ref": "docs/handover/bast-signed-2026.pdf",
  "operator_demo_ref": "docs/handover/tot-operator-walkthrough-2026.md",
  "access_receipt_ref": "docs/handover/vault-cutover-manifest.json"
}
```

### Strict TypeScript Per-Item BAST Cutover State Evaluator
```typescript
export type HandoverItemStatus = 'VERIFIED' | 'PENDING';

export interface HandoverDeliverableItem {
  readonly itemId: string;
  readonly name: string;
  readonly digestMatches: boolean;
  readonly signaturePresent: boolean;
  readonly vaultAccessible: boolean;
  readonly exceptionNote: string | null;
}

export function evaluateBastItemStatus(
  item: HandoverDeliverableItem,
): { readonly status: HandoverItemStatus; readonly blockers: readonly string[] } {
  const blockers: string[] = [];
  if (!item.digestMatches) {
    blockers.push('ARTIFACT_DIGEST_MISMATCH');
  }
  if (!item.signaturePresent) {
    blockers.push('MISSING_AUTHORIZED_SIGNATURE');
  }
  if (!item.vaultAccessible) {
    blockers.push('VAULT_SECRET_INACCESSIBLE');
  }
  return {
    status: blockers.length === 0 ? 'VERIFIED' : 'PENDING',
    blockers,
  };
}
```

### Mandatory Source & Technical Asset Inventory Matrix
| Asset Category | Contracted Contents | Provenance Proof | Collaborating Skill |
| :--- | :--- | :--- | :--- |
| **Source Repositories** | Frontend, Backend, Mobile, ETL, Docker/IaC configs | Exact Git commit SHA + bundle `contract_sha256` | `/shadow-release`, `/shadow-ops` |
| **Database Assets** | `schema.dbml`, `ERD.md`, migration history, clean reference seeds | Clean dry-run migrate + seed receipt | `/shadow-db`, `/shadow-data` |
| **API & Integration Specs** | `openapi.yaml`, existing Postman/Bruno collection, webhook HMAC specs | Validated OpenAPI + collection export | `/shadow-api`, `/shadow-integrate` |
| **SBOM & Licenses** | CycloneDX/SPDX SBOM from frozen lockfile + OSS license policy check | Zero prohibited GPL/unlicensed blockers | `/shadow-supplychain` |

## 5. Platform / Vendor Variations
- **Indonesian Government / BUMN (`SPK` / `KAK` / `BAST`)**: Structure `BAST` annexes strictly mirroring KAK deliverable numbering (`templates/17_HANDOVER.md` via `/shadow-doc`), include `Berita Acara Pemeriksaan Pekerjaan (BAPP)` alignment, and distinguish **PHO (Provisional Handover)** from **FHO (Final Handover after warranty period)**.
- **Private Enterprise & M&A Transfers**: Emphasize IP clean-room license compliance (CycloneDX SBOM), CI/CD secret migration to client cloud accounts, and reproducible container image builds from client-owned registries.

## 6. Decision Matrix & Trade-Offs
| Handover Condition | BAST Verdict | Required Action |
| :--- | :--- | :--- |
| All 7 packages verified (`check_receipt.py` PASS + human review + operator restore demo) | **Full BAST Sign-Off** | Issue final BAST annex + activate warranty SLA (`/shadow-maintain`) |
| 6 packages verified, 1 item has missing signature or vault mismatch | **Partial / Conditional Handover** | Mark exact unverified item `PENDING` with remediation owner & date; never mark `VERIFIED` |
| Digest mismatch between delivered archive and signed receipt | **HARD BLOCK** | Rebuild deterministic archive from immutable commit SHA and re-verify before signing |

## 7. Real Production Scenario
**Context:** A system integrator handed over a ministry application via a shared Google Drive zip titled `final_app_v2_revisi3.zip` with no commit SHA, no SBOM, and no receipt digest. Three months later, when the agency's internal team tried to patch a CVE, the source code in the zip failed to build because it was missing 12 hotfix commits that had been deployed straight to Production.
**Fix:** Enforcing `check_receipt.py` against an immutable release tarball bound to exact Git SHA + `contract_sha256`, CycloneDX SBOM, and clean-checkout build proof guaranteed the delivered source matched Production byte-for-byte.

## 8. Failure Modes & Edge Cases
- **WRONG (Treating `check_receipt.py` exit code 0 as complete legal/operational proof):** Relying purely on automated JSON field presence without opening the signed PDF or watching the client operator restore a backup.
  **RIGHT:** Use `check_receipt.py` for cryptographic digest & reference completeness, AND require human verification of signatory authority and live operator walkthrough evidence.
- **WRONG (Editing generated `BAST.docx` directly or calling `/handoff` MCP for client BAST):** Breaks source-to-output provenance or confuses AI context handoff with formal contract delivery.
  **RIGHT:** Maintain BAST sources in Canonical JSON AST / Markdown rendered via `shadow-doc/scripts/doc_orchestrator.py`, and reserve `/handoff` exclusively for AI session context transfer.

## 9. Testing & Verification
- Run `python -m unittest discover -s shadow-handover/tests -v` (`test_receipt.py` & `test_partial_handover_cutover.py`).
- Verify `python shadow-handover/scripts/check_receipt.py <artifact> <receipt.json>` returns exit code `0` for valid receipts and fails closed on tampered digests or missing mandatory refs.

## 10. Operational Considerations
- Archive the signed BAST PDF, `receipt.json`, `manifest.json` (`SHA-256`), and UAT evidence archive in immutable client-owned storage for statutory contract audit retention (`>= 5` years in Indonesian public procurement).

## 11. Authoritative References
- **ISO/IEC/IEEE 12207:2017** — *Transition Process & Operational Handover*.
- **Shadow Doc Engine** — `shadow-doc/templates/17_HANDOVER.md` & `shadow-doc/scripts/doc_orchestrator.py`.
- **Shadow Supplychain** — CycloneDX 1.5 / SPDX SBOM provenance standards.

## 12. Limitations & When NOT to Use
- **Do NOT use** `/shadow-handover` to save or resume AI agent conversation memory — use `/handoff` (`shadow_handoff` MCP).
- **Do NOT use** `/shadow-handover` to push Git release tags or execute production deployments without `L4` authorization — coordinate release mechanics with `/shadow-release`.
