# DATABASE — Schema, Queries, Transactions & Migrations

The database is the source of persistent truth. Treat it as core system design, not a detail behind an ORM.

## 1. Schema design

For every table decide: primary key type (bigint identity vs UUID/ULID — UUIDv7/ULID for sortable distributed IDs),
foreign keys and `ON DELETE` behavior, unique constraints, nullability, defaults, check constraints, indexes,
normalization level, lifecycle (retention, archival, deletion), and who owns it.

Ask first: **what queries will run against this table?** Design indexes from real access patterns:
- Composite index column order follows equality filters first, then range/sort columns.
- Index foreign keys used in joins and cascades.
- Covering/partial indexes for hot paths; avoid indexing everything (writes pay for each index).
- Check plans with `EXPLAIN` / `EXPLAIN ANALYZE` (PostgreSQL), `EXPLAIN` (MySQL), execution plans (SQL Server).

Types: `timestamptz`/UTC for instants; `numeric/decimal` or integer minor units for money; proper enum/lookup tables or
check constraints for statuses; `text` with length validation over arbitrary `varchar(255)` where the DB allows.

## 2. Constraints enforce invariants

Applications have bugs; constraints are the last line of defense. Enforce in the DB as well as in code when possible:
unique email (case-insensitive: unique index on `lower(email)` or `citext`), unique transaction/provider reference,
FK integrity, non-null requirements, valid ranges (`CHECK (quantity >= 0)`), one active record per owner (partial unique index).
Handle the resulting unique-violation error as a `ConflictError`, not a 500.

## 3. Transactions

- Wrap multi-step state changes that must succeed or fail together (order + items + stock reservation + payment record).
- Keep transactions short. **Never call external APIs, send email or publish to a broker inside a DB transaction** —
  use the outbox pattern (write an outbox row in the same transaction; a relay publishes it).
- Always roll back on error (use the framework's scoped transaction helper).
- Choose isolation deliberately; know the default (PostgreSQL/SQL Server: READ COMMITTED; MySQL InnoDB: REPEATABLE READ).
  Handle serialization failures/deadlocks with bounded retry of the whole transaction.
- Concurrency tools, simplest first: atomic conditional update → unique constraint → optimistic lock (`version` column,
  `WHERE id = ? AND version = ?`, check affected rows) → pessimistic lock (`SELECT … FOR UPDATE`, lock in consistent order
  to avoid deadlocks) → advisory/distributed lock.
- Remote systems cannot be rolled back by a DB transaction: saga, compensating actions, idempotency.

## 4. Migrations

Never casual. For production consider backward compatibility, existing data, lock duration, migration runtime,
deploy ordering (old and new app versions run side by side during rollout) and rollback.

Expand → migrate → contract for risky changes:
1. Add new nullable column/table (expand). 2. Deploy code that writes both / reads with fallback.
3. Backfill in batches (small chunks, throttled, resumable, observable, idempotent). 4. Switch reads.
5. Add constraints (PostgreSQL: `NOT VALID` then `VALIDATE CONSTRAINT`). 6. Remove old column in a later release (contract).

Rules:
- Never drop or rename a column that running code uses in the same deploy.
- Large tables: create indexes concurrently (`CREATE INDEX CONCURRENTLY` in PostgreSQL; online DDL in MySQL 8 /
  SQL Server Enterprise); avoid table rewrites (volatile defaults, type changes) during peak hours.
- Migrations are versioned, reviewed, reversible where feasible, and never edited after being applied to shared environments.
- Changing a field's meaning requires a migration and communication, not a silent reinterpretation.
- Schema evolution for APIs/messages follows the same rule: additive first, old and new consumers coexist.

## 5. Queries and ORM discipline

ORMs are tools, not a substitute for SQL knowledge. Know the SQL they generate (enable query logging in dev).
Watch for:
- **N+1 queries** — use joins/eager loading/batch loading deliberately (`include`, `Include`, `select_related/prefetch_related`,
  `with()`, `JOIN FETCH`, DataLoader).
- Over-eager loading of huge graphs; `SELECT *` on hot paths — select needed columns.
- Unbounded queries — every list has `LIMIT`; exports stream or paginate.
- Functions on indexed columns in `WHERE` (defeat indexes), leading-wildcard `LIKE '%x'`, implicit type casts.
- `OFFSET` on deep pages of large tables — switch to keyset pagination (`WHERE (created_at, id) < (?, ?)`).
- Long-held connections and connection leaks; size pools to DB limits (instances × pool size ≤ max connections, leave headroom).
Use raw SQL when it is clearer or much faster, always parameterized, and keep it in the repository layer.
Never concatenate user input into SQL; ORDER BY/column names from input must go through an allowlist.

## 6. Soft delete, multi-tenancy, audit

- Soft delete (`deleted_at`) is not a default. It requires every query to filter it, complicates unique constraints
  (use partial unique indexes `WHERE deleted_at IS NULL`), and conflicts with erasure requirements. Use it when there is a real restore/audit need.
- Multi-tenancy: shared schema with `tenant_id` (cheapest, needs strict enforcement — consider PostgreSQL Row-Level Security),
  schema-per-tenant, or database-per-tenant (strongest isolation, highest ops cost). Every query path enforces tenant scope;
  never trust a client-supplied tenant ID without authorization. Include `tenant_id` in composite indexes and unique constraints.
- Audit/history tables for important state transitions; do not overwrite what the business needs to reconstruct.

## 7. Destructive operations

Before `DROP`, `TRUNCATE`, `DELETE`, `UPDATE` without a tight `WHERE`, or destructive `ALTER`:
confirm the environment, back up (and know how to restore), count affected rows first with a `SELECT` using the same
`WHERE`, run inside a transaction when possible and check the row count before `COMMIT`, check FK cascades,
and have a rollback plan. Never casually recommend destructive SQL against production.

## 8. Backups & recovery

Define frequency, retention, encryption, off-site copies, point-in-time recovery needs, RPO and RTO. Test restores
regularly — an untested backup is a hope, not a backup. Never use raw production data in dev/staging; anonymize.

## 9. Caching around the DB

Every cache: what, where, TTL, invalidation on write, stale tolerance, stampede protection (single-flight/locks,
jittered TTL), behavior on cache failure. Cache invalidation is application logic, not an afterthought.

## 10. Database checklist

Keys and FKs correct · constraints enforce invariants · indexes match queries (plans checked) · no N+1 · lists paginated
and bounded · transactions short with no network calls · race conditions handled · migration is backward compatible and
reversible or has a plan · backfill batched · soft delete/tenant filters consistent · PII classified · backups restorable.
