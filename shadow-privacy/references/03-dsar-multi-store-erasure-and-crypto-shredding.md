# 03. DSAR, Multi-Store Erasure & Crypto-Shredding

## 1. Purpose & Activation Conditions
Architect complete Data Subject Access, Portability, Rectification, Restriction, and **Multi-Store Erasure (`DSAR`)** workflows covering primary databases, search indexes, caches, third-party processors, backups, and statutory legal-hold exceptions (`UU PDP Pasal 5–13, 42–44`; `GDPR Art. 15–20`). Load when building account deletion, data export, retention TTL jobs, or synthetic erasure rehearsals.

## 2. Prerequisites
- Complete independently established inventory (`expected_stores`) of every internal store and external vendor holding subject identifiers (primary DB, Redis cache, OpenSearch, warehouse, PostHog/GA4/Mixpanel, ESP, backups).

## 3. Technical Principles & Constraints
- **Full Data Subject Rights Coverage (`UU PDP BAB IV`):**
  - **Access & Portability (`Pasal 7 & 13`):** Verify caller identity first (prevent account-hijack data export!), return structured machine-readable JSON/CSV excluding other individuals' PII or internal trade secrets.
  - **Rectification & Restriction (`Pasal 6 & 11`):** Allow profile correction with audit trail; support `processing_restricted = true` freezing analytics/mutations during disputes.
  - **Erasure (`Pasal 8 & 43`):** Deleting only the primary `users` row (or only `analytics_identity_map`) is **INCOMPLETE**. True erasure traces ALL stores (`expected_stores`), invokes third-party processor deletion APIs, records redacted **evidence receipts**, and explicitly tracks **backup/archive expiry windows** as pending until natural TTL expiration!
- **Statutory Legal-Hold Coexistence (`Pasal 20(2)(c)`):** Financial/tax invoices (e.g., 10-year Indonesian tax retention) cannot be illegally destroyed during user erasure — separate statutory accounting ledgers under `LEGAL_OBLIGATION`, strip non-statutory profile/marketing/behavioral data, and retain ONLY a minimal keyed **`HMAC-SHA256` suppression tombstone** so erased users are never re-imported into marketing lists!
- **Crypto-Shredding for Immutable Logs / Append-Only Stores:** When rewriting terabytes of append-only snapshots per user is impractical, encrypt each subject's PII with a dedicated per-subject Data Encryption Key (`subject_dek`) stored in KMS/key-table; destroying `subject_dek` renders historical ciphertexts cryptographically unrecoverable (validate legal adequacy with Legal/DPO!).
- **Synthetic Rehearsal Discipline (`privacy_pdp_auditor.py --assess-erasure`):** Always rehearse erasure end-to-end using **`synthetic: true`** dummy subjects and redacted system aliases — NEVER put real customer PII inside audit evidence manifests, and NEVER mark a rehearsal closed while ANY processor receipt is absent or retained archive remains unreviewed!

## 4. Architecture & Implementation
```powershell
# Rehearse & validate multi-store synthetic DSAR erasure manifest offline (L1)
python "shadow-privacy/scripts/privacy_pdp_auditor.py" --assess-erasure path/to/erasure_manifest.json
python -m unittest discover -s "shadow-privacy/tests" -v
```
Multi-Store Erasure Receipt State Machine:
```typescript
export type StoreErasureStatus = 'DELETED_LIVE' | 'CRYPTO_SHREDDED' | 'RETAINED_LEGAL_HOLD' | 'PENDING_BACKUP_EXPIRY' | 'PENDING_PROCESSOR_RECEIPT';

export interface StoreErasureReceipt {
  readonly storeAlias: string; // Redacted alias e.g. 'primary_pg', 'vendor_posthog', 'wal_backups'
  readonly status: StoreErasureStatus;
  readonly evidenceRef: string; // Opaque job/ticket ID — ZERO raw personal data!
  readonly legalBasisIfRetained?: 'LEGAL_OBLIGATION';
  readonly expectedExpiryIso?: string;
}

export function isDsarRehearsalClosed(
  expectedStores: readonly string[],
  receipts: readonly StoreErasureReceipt[]
): { readonly closed: boolean; readonly openReasons: readonly string[] } {
  const byStore = new Map(receipts.map((r) => [r.storeAlias, r]));
  const openReasons: string[] = [];

  for (const store of expectedStores) {
    const rec = byStore.get(store);
    if (!rec) {
      openReasons.push(`MISSING_RECEIPT:${store}`);
      continue;
    }
    if (rec.status === 'PENDING_PROCESSOR_RECEIPT' || rec.status === 'PENDING_BACKUP_EXPIRY') {
      openReasons.push(`${rec.status}:${store}`);
    }
    if (rec.status === 'RETAINED_LEGAL_HOLD' && rec.legalBasisIfRetained !== 'LEGAL_OBLIGATION') {
      openReasons.push(`UNJUSTIFIED_RETENTION:${store}`);
    }
  }
  return { closed: openReasons.length === 0, openReasons };
}
```

## 5. Platform / Vendor Variations
| Store Type | Erasure Mechanism | Status Semantics |
| :--- | :--- | :--- |
| **Primary Postgres / MySQL** | Hard delete / anonymize PII columns + purge Redis session/cache keys | `DELETED_LIVE` (synchronous) |
| **Search Index (OpenSearch/Meilisearch)** | Delete document by `subject_id` + verify refresh | `DELETED_LIVE` |
| **3rd-Party Vendors (PostHog, GA4, Mixpanel, Resend)** | Official deletion API + webhook/poll confirmation receipt (`/shadow-analytics` Module `04`) | `PENDING_PROCESSOR_RECEIPT -> DELETED_LIVE` |
| **Encrypted Point-in-Time Backups (30d TTL)** | Do NOT mutate immutable backups; maintain post-restore replay suppression log + TTL expiry | `PENDING_BACKUP_EXPIRY` until backup ages out |

## 6. Decision Matrix & Trade-Offs
| Deletion Technique | Speed | Auditability | Best Used For |
| :--- | :---: | :---: | :--- |
| **Hard Row Delete + Cascade** | Fast | High | Ephemeral profiles, drafts, tokens, caches, search docs |
| **Irreversible Pseudonymization (`user_<hash>` + NULL PII)** | Fast | High | Preserving referential integrity on statutory financial/order rows |
| **Per-Subject Crypto-Shredding** | Instant key wipe | High (key destruction log) | Large immutable archives & event lakes |

## 7. Real Production Scenario
A SaaS app runs `DELETE FROM users WHERE id = $1` on account deletion, then marks the DSAR ticket `"Complete"`. Two weeks later, a disaster-recovery test restores a 20-day-old backup, resurrecting erased users — AND the marketing ESP + PostHog still contain the erased customer's email and behavioral history. Upgrading to an orchestrated DSAR workflow verified with `privacy_pdp_auditor.py --assess-erasure` (requiring receipts for all `expected_stores`, maintaining a post-restore erasure replay ledger, and keeping hashed suppression tombstones) closes every gap.

## 8. Failure Modes & Edge Cases
- **WRONG:** Executing DSAR erasure on unauthenticated requests or without verifying subject identity (lets an attacker delete a victim's account or steal their data export!).
- **RIGHT:** Authenticate & verify subject identity (with step-up auth for exports/deletions) before initiating any DSAR flow.
- **WRONG:** Storing raw `email` or `nik` inside the DSAR completion log (`"Deleted budi@example.com, NIK 3174..."`).
- **RIGHT:** Log ONLY opaque `request_id`, redacted system aliases, hashed subject digest, and external processor job reference IDs.

## 9. Testing & Verification
- Run `python -m unittest discover -s shadow-privacy/tests -v` (`test_erasure.py` verifies synthetic erasure rehearsal, missing processor receipts, and pending backup archive checks).

## 10. Operational Considerations
- Automate scheduled retention TTL jobs (`Pasal 42`) for inactive accounts, expired staging dumps (NEVER copy unmasked prod PII into staging/QA!), and raw clickstream logs so personal data never accumulates indefinitely.

## 11. Authoritative References
- UU PDP (UU No. 27 Tahun 2022) — Pasal 5–13 & Pasal 42–44.
- EU GDPR — Articles 15–20 (*Data Subject Rights*).

## 12. Limitations & When NOT to Use
- Automated DSAR orchestration cannot resolve contested legal holds (active litigation, fraud investigations, tax audits) autonomously — route flagged accounts (`legal_hold = true`) to DPO/Legal review before execution.
