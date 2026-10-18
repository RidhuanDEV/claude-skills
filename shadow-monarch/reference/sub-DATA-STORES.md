# sub-DATA-STORES — Authoring Rules for PostgreSQL, Redis, Elasticsearch/OpenSearch & MongoDB

Use when writing engine-specific queries, indexes, migrations, caching layers, or search pipelines for PostgreSQL,
Redis, Elasticsearch/OpenSearch, or MongoDB. Pair with `DATABASE.md` for general relational/transaction design.

## 1. PostgreSQL specific authoring rules

- **Data types**:
  - Use `TIMESTAMPTZ` (never `TIMESTAMP WITHOUT TIME ZONE`), `UUID` (prefer UUIDv7 for time-ordered index locality),
    `TEXT` or bounded `VARCHAR(N)`, `NUMERIC(precision, scale)` or `BIGINT` minor units for money, and `JSONB` (never `JSON`).
- **Indexing discipline**:
  - **B-Tree** (default) for equality and range queries; order composite index columns by equality predicates first,
    then range/sort columns.
  - **GIN index** for `JSONB` containment (`@>`) and full-text `tsvector`; use `jsonb_path_ops` when only `@>` is needed.
  - **Partial index** (`CREATE INDEX ... WHERE deleted_at IS NULL AND status = 'ACTIVE'`) to shrink index size and speed up hot queries.
  - Always create/drop indexes with `CREATE INDEX CONCURRENTLY` in production migrations (outside a transaction block) so writes are not locked.
- **Locking, Upserts & Concurrency**:
  - Atomic upsert: `INSERT INTO ... ON CONFLICT (natural_key) DO UPDATE SET ... EXCLUDED...`.
  - Job queue / row claiming: `SELECT ... FOR UPDATE SKIP LOCKED LIMIT N`.
- **Row-Level Security (RLS) & Multi-Tenancy**:
  - When enforcing tenant isolation via Postgres RLS, set `app.current_tenant_id` via transaction-local `SET LOCAL`
    (`set_config('app.current_tenant_id', $1, true)`) so pooled connections never leak tenant context across requests.
- **`pgvector` similarity search**:
  - Create **HNSW** index (`USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64)`); pre-filter by
    indexed metadata columns (`tenant_id`, `status`) and use iterative scan in modern `pgvector` versions so filtered KNN returns full `LIMIT K`.

## 2. Redis authoring rules

- **Key naming convention**: `<env>:<service>:<domain>:<entity>:<id>:<attribute>` (e.g., `prod:order-svc:cart:user:9481:items`).
- **Mandatory TTL**: every cache key MUST be written with an explicit expiration (`EX` / `PX`) plus small random jitter
  (e.g., $\pm 10\%$) to prevent cache stampede when thousands of keys expire at the exact same second.
- **Never block the single-threaded event loop**:
  - **NEVER** run `KEYS *`, `FLUSHALL`, or unbounded `SMEMBERS`/`HGETALL` on giant collections in production. Use `SCAN` /
    `HSCAN` / `SSCAN` with bounded count, and `UNLINK` instead of `DEL` for large keys.
- **Atomicity & pipelining**:
  - Use **Pipelines** to batch multiple round-trips.
  - Use **Lua scripts (`EVAL`/`EVALSHA`)** for atomic read-check-modify operations (rate limiters, token buckets, lock release:
    verify lock owner token before `DEL` so an expired lock holder never deletes another worker's lock).

## 3. Elasticsearch / OpenSearch authoring rules

- **Explicit index mappings (`dynamic: "strict"` or `"false"` in prod)**:
  - Never rely on dynamic mapping in production (a single malformed string in a numeric field breaks ingestion or creates
    mapping explosion).
  - Use `keyword` for exact filters, IDs, enums, sorting, and aggregations; use `text` with appropriate analyzer for full-text search.
- **Query performance**:
  - Put exact filters (`tenant_id`, `status`, date ranges) inside the `bool.filter` clause (cached, zero scoring CPU cost)
    and reserve `bool.must` / `bool.should` for relevance-scored full-text queries.
  - Deep pagination: never use `from + size > 10,000`; use `search_after` with a deterministic tie-breaker sort (`[score, _id]`).
- **Zero-downtime reindexing**: read/write through an **Index Alias** (`orders_current` → `orders_v2`); when mappings change,
  create `orders_v3`, reindex in background, and atomically swap the alias.

## 4. MongoDB authoring rules

- **Schema validation at collection level**: enforce `$jsonSchema` validation rules on collections plus strict application-level
  schema parsing (Zod/Mongoose with `strict: 'throw'` and `strictQuery: true`).
- **NoSQL operator injection defense**: reject or strip keys starting with `$` or containing `.` from untrusted user input
  before passing to `find()` / `updateOne()`.
- **Document growth & indexing**:
  - Never embed unbounded arrays (e.g., storing millions of log events inside a single `User` document hits the 16MB BSON limit);
    use the Bucket or Outlier pattern and reference by ID.
  - Follow the **ESR rule (Equality → Sort → Range)** when ordering fields in compound indexes, and verify with `.explain("executionStats")` that `totalDocsExamined` matches `nReturned` (zero `COLLSCAN` on large collections).
