# Client BAST Handover, Shift Access Cutover & Operator Readiness Playbook

> Use this playbook when delivering BAST (Berita Acara Serah Terima), executing zero-plaintext credential & vault ownership cutover, preparing Admin/Operator/User manuals, running Training of Trainers (ToT), and transitioning SLA support to `/shadow-maintain`. *(Distinct from `/handoff` AI session memory).*

## 1. Core Concepts
A software delivery isn't truly handed over when Git access is shared—it is handed over when the client **owns clean reproducible builds, verified runtime access, rotated non-plaintext secrets, complete SBOM/source provenance, and proven operator self-sufficiency** with previous vendor credentials revoked:
- **Access Cutover Invariant:** Handover access is verified ONLY when `old_vendor_access_revoked === true AND new_client_admin_verified === true`.
- **Single Document Engine Boundary (`SA-DOC-ENGINE-001`):** Author BAST and manual sources in `.md` / Canonical AST JSON and render formal `.docx`/`.pdf` outputs strictly through `shadow-doc/scripts/doc_orchestrator.py` — never embed duplicate renderers.

## 2. Technical Rules & Decision Matrix

| Handover Component | Required Content | Verification Proof |
| :--- | :--- | :--- |
| **Source, SBOM & Release Inventory** | Tagged repo SHA, lockfiles, CycloneDX SBOM, `contract_sha256` | `python shadow-handover/scripts/check_receipt.py ARTIFACT RECEIPT.json` |
| **Credential & Access Transfer Manifest** | Secret Vault refs/paths ONLY (**0 plaintext secrets**), IAM role map | Client confirms rotation + login; old vendor tokens revoked & logged |
| **Admin / Operator / User Manuals** | Setup from clean checkout, env/backup/restore, log triage, rollback runbook | Dry-run walkthrough executed cleanly by client operator (`operator_demo_ref`) |
| **Berita Acara Serah Terima (BAST)** | Scope delivered, warranty SLA window, open minor punch-list, signatures | Rendered via `shadow-doc/scripts/doc_orchestrator.py` (`adapt_handover_payload`) |

## 3. Implementation Examples

### Zero-Plaintext Credential Transfer & Receipt JSON (`scripts/check_receipt.py`)
```json
{
  "release": "v1.4.0",
  "contract_ref": "SPK-2026-089/IT-GOV",
  "sender": "vendor-delivery-lead@example.org",
  "recipient": "client-it-head@example.go.id",
  "criteria": "All P0/P1 UAT scenarios passed; backup restore drill RTO=18m verified.",
  "warranty_owner": "vendor-support-l2@example.org (Harwat 90d)",
  "contract_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "signed_receipt_ref": "docs/handover/bast-signed-2026.pdf",
  "operator_demo_ref": "docs/handover/tot-operator-walkthrough-2026.md",
  "access_receipt_ref": "docs/handover/vault-cutover-manifest.json"
}
```
```json
{
  "vault_cutover": [
    {
      "service": "primary-postgres-prod",
      "secret_ref": "<SECRET_REF:prod/db/admin>",
      "vault_path": "vault://kv-prod/data/core/postgres",
      "client_owner_role": "client-dba-admin",
      "old_vendor_access_revoked": true,
      "new_client_access_verified": true,
      "rotated_at_utc": "2026-05-01T08:30:00Z"
    }
  ]
}
```

## 4. Best Practices
- Make the client operator physically perform one **backup restore**, one **log/health inspection**, one **secret rotation**, and one **staging rollback drill** during Training of Trainers (ToT) before recording `operator_demo_ref`.
- Package one standalone deliverable bundle listing exact runtime versions (`Node`, `PostgreSQL`, `Redis`, OS) plus dependency license & SBOM summaries (`/shadow-supplychain`).

## 5. Anti-Patterns (`WRONG` vs `RIGHT`)
- **WRONG (Sending plaintext passwords in Word/WhatsApp/Excel or skipping vendor revocation):** Putting live `DB_PASSWORD=...` inside `BAST.docx` or leaving vendor personal SSH keys / OAuth apps active post-BAST.
  **RIGHT:** Store vault references + rotation proof in a manifest, verify client admin login first, then revoke all temporary vendor credentials cleanly.
- **WRONG (Editing generated `.docx` directly or confusing `/handoff` with `/shadow-handover`):** Manually patching `.docx` files or running `save_handoff` MCP when the Monarch requests formal client BAST handover.
  **RIGHT:** Always edit Markdown/Canonical sources + regenerate via `shadow-doc/scripts/doc_orchestrator.py`, and use `/shadow-handover` for client BAST (`handoff` is strictly AI context transfer).

## 6. Production Considerations
- **Warranty Transition:** Hand off runbooks, SLO alert contacts, and unresolved minor `SEV4` punch-list items explicitly to the `/shadow-maintain` Harwat support workflow at cutover sign-off.
