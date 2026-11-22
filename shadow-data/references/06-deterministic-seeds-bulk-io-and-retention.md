# 06. Deterministic Seeds, Bulk I/O & Retention Lifecycle

## 1. Purpose & Activation Conditions
Design idempotent database seeds (safely separating system reference data from production-blocked demo fixtures), memory-bounded bulk CSV/Excel imports & streaming exports, and resurrection-proof retention/erasure lifecycles. Load when writing `db:seed`, CSV import/export endpoints, or data archival/deletion jobs.

## 2. Prerequisites
- Schema constraints (`shadow-db` Module `01`), LRO `202 Accepted` async pattern (`shadow-api` Module `06`), and privacy retention/erasure policy (`shadow-privacy` Module `03`).

## 3. Technical Principles & Constraints
- **Deterministic Idempotent Seeding (`db:seed`):**
  - Every seed MUST use **`INSERT ... ON CONFLICT (...) DO UPDATE` / `DO NOTHING`** so running `db:seed` 10 times produces identical state with zero errors and zero duplicate rows!
  - **Strict System vs Demo Separation:** Separate mandatory **System Reference Seeds** (roles, permissions, ISO currencies, Indonesian province/city codes — safe & deterministic in production) from **Demo/Dummy Seeds** (test accounts, fake invoices — MUST **fail closed** if `NODE_ENV === 'production'` or `APP_ENV === 'production'`!).
- **Memory-Safe Bulk Import (CSV / Excel):**
  1. Stream-parse rows (never buffer entire 100MB spreadsheets into memory),
  2. Validate EVERY row against typed schema rules upfront (collecting exact `{ rowNumber, column, errorCode }` diagnostics),
  3. Insert in bounded transactional batches (`500–1,000` rows per multi-row `INSERT` or PostgreSQL `COPY`), using `ON CONFLICT` idempotency for resumable retries!
- **Memory-Safe Streaming Bulk Export:**
  - NEVER run `await db.invoices.findMany()` loading `250,000` rows into Node/Python RAM!
  - Stream via **keyset cursor batches** (`1,000` rows at a time) piped straight to HTTP chunked stream or S3 presigned download via `202 Accepted` LRO (`shadow-api`).
  - **CSV Formula Injection Defense:** Prefix any user-authored cell starting with `=`, `+`, `-`, `@`, `\t`, or `\r` with a single quote `'` (or safe tab neutralization) so exported CSVs never execute Excel macro formulas on admin laptops!
- **Retention, Partition Pruning & Resurrection-Proof Erasure:**
  - Automate scheduled retention TTL cleanup (`UU PDP Pasal 42`) via monthly partition drops (`DROP TABLE audit_2025_01`) or throttled keyset batch deletes (never unbounded single-tx `DELETE FROM logs WHERE created_at < ...`!).
  - Maintain an external **Erasure Tombstone Ledger** (hashed subject ID, respecting `legal_hold = true`) replayed immediately after any backup restore before traffic resumes (`/shadow-privacy`, `/shadow-resilience`).

## 4. Architecture & Implementation
```typescript
const FORMULA_PREFIX = /^[=+\-@\t\r]/;

// Neutralizes CSV/Excel formula injection (CWE-1236) cleanly
export function escapeCsvCellSafe(rawValue: string | number | null | undefined): string {
  const str = rawValue === null || rawValue === undefined ? '' : String(rawValue);
  const neutralized = FORMULA_PREFIX.test(str) ? `'${str}` : str;
  if (/[",\r\n]/.test(neutralized)) {
    return `"${neutralized.replace(/"/g, '""')}"`;
  }
  return neutralized;
}

// Fail-closed guard preventing accidental demo fixture seeding in production
export function assertNonProductionDemoSeed(envName: string | undefined): void {
  const normalized = (envName ?? '').trim().toLowerCase();
  if (normalized === 'production' || normalized === 'prod') {
    throw new Error('DEMO_SEED_BLOCKED_IN_PRODUCTION: Refusing to insert dummy fixtures into production.');
  }
}
```
Idempotent system reference seed (PostgreSQL):
```sql
INSERT INTO roles (code, display_name, is_system)
VALUES
  ('admin', 'Tenant Administrator', TRUE),
  ('approver', 'Finance Approver', TRUE),
  ('viewer', 'Read-Only Viewer', TRUE)
ON CONFLICT (code) DO UPDATE
SET display_name = EXCLUDED.display_name,
    is_system    = EXCLUDED.is_system;
```

## 5. Platform / Vendor Variations
| Bulk I/O Pattern | Recommended Mechanism | Watch-Out |
| :--- | :--- | :--- |
| **PostgreSQL Bulk Load (`> 50k` rows)** | `COPY ... FROM STDIN` into staging temp table -> validate -> `INSERT ... ON CONFLICT` | Fastest (10x–50x faster than row-by-row ORM inserts) |
| **Large Admin CSV Export (`> 10k` rows)** | Async `202 Accepted` LRO worker streaming keyset chunks -> S3 presigned download | Enforces tenant isolation (`tenant_id`) + short-lived (`15m`) download URL |
| **Staging / QA Database Seeding** | Synthetic generator + system reference seed — **NEVER raw production PII dumps!** | Unmasked prod dumps in staging violate UU PDP `Pasal 35 & 42` |

## 6. Decision Matrix & Trade-Offs
| Deletion / Retention Mechanism | Lock / Bloat Impact | Best Used For |
| :--- | :---: | :--- |
| **Monthly Partition `DROP TABLE`** | **Instant (`0` dead tuples!)** | Logs, audit trails, telemetry, outbox archives |
| **Throttled Keyset Batch `DELETE` (`1,000` rows + pause)** | Low & controlled | Non-partitioned tables with selective TTL expiry |
| **Unbounded `DELETE FROM tbl WHERE created_at < ...`** | **SEVERE (locks + massive MVCC bloat)** | **NEVER run on large live tables** |

## 7. Real Production Scenario
An admin clicks `"Export 2026 Orders (CSV)"` (280,000 rows). The API runs `prisma.order.findMany()` into RAM, crashing the 512MB container with OOMKill every time — AND a malicious vendor entered `=HYPERLINK("https://evil.test","Click")` as their company name, risking Excel formula execution on Finance laptops! Converting exports to an async `202 Accepted` keyset-streaming worker using `escapeCsvCellSafe` holds worker RAM flat at `< 40 MB` and neutralizes CSV injection cleanly.

## 8. Failure Modes & Edge Cases
- **WRONG:** Leaving `db:seed` as a single script that inserts `admin@test.com / password123` alongside mandatory role codes (running it on prod creates a known backdoor admin account!).
- **RIGHT:** Physically separate `seed:system` (roles/lookups only, idempotent `UPSERT`) from `seed:demo` (guarded by `assertNonProductionDemoSeed` + verified via `data_migration_plan_verifier.py --check-seed-safety`).
- **WRONG:** Committing partial CSV import batches without telling the user which exact rows failed (leaves half-imported files with no idempotent re-upload key).
- **RIGHT:** Pre-validate rows and return a structured per-row error report, or attach an `import_batch_id` + `external_row_key` for safe idempotent re-runs.

## 9. Testing & Verification
- Run `python shadow-data/scripts/data_migration_plan_verifier.py --check-seed-safety <seed.json>`.
- Test idempotency: run `seed:system` twice back-to-back and assert identical row counts and zero exceptions; test `seed:demo` with `NODE_ENV=production` and assert it exits non-zero with zero writes!

## 10. Operational Considerations
- Monitor bulk export/import job duration, row volume, and failure rates; enforce per-tenant concurrent export quotas (`<= 2` active jobs) so one tenant cannot starve shared worker pools.

## 11. Authoritative References
- OWASP — *CSV Injection (Formula Injection / CWE-1236)* (`https://owasp.org/www-community/attacks/CSV_Injection`).
- PostgreSQL Documentation — *Populating a Database (`COPY` & Bulk Load Best Practices)* (`https://www.postgresql.org/docs/current/populate.html`).

## 12. Limitations & When NOT to Use
- Do NOT implement custom streaming CSV ingestion pipelines for ad-hoc one-off 50-row lookups; keep small bounded admin uploads (`< 1,000` rows) clean with single-transaction schema validation.
