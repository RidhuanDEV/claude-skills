# 01. Relational Design & Integrity Invariants

## 1. Purpose & Activation Conditions
Design normalized, constraint-enforced relational schemas that uphold data integrity directly inside the database engine (monetary precision, tenant scoping, temporal clarity, partial uniqueness under soft deletes). Load when modeling new tables, reviewing ERDs (`shadow_db` MCP), or auditing schema integrity defects.

## 2. Prerequisites
- Domain invariants from `/shadow-domain` and privacy field classification from `/shadow-privacy` (`UU PDP Pasal 4`).

## 3. Technical Principles & Constraints
- **Database Enforces Last-Line Invariants:** Application code bugs, concurrent requests, and ad-hoc scripts bypass ORM validations. Always back critical invariants with database-level `PRIMARY KEY`, `NOT NULL`, `UNIQUE`, `CHECK`, and `FOREIGN KEY` constraints!
- **Monetary & Temporal Precision (Zero Silent Corruption):**
  - Store currency strictly as **`BIGINT` integer minor units** (e.g., `total_minor` in Rupiah/cents + ISO-4217 `currency CHAR(3)`) or **`NUMERIC(19, 4)`** — NEVER `FLOAT`, `REAL`, or `DOUBLE PRECISION`!
  - Store instants strictly as UTC **`TIMESTAMPTZ`** (`DATETIME(6)` UTC in MySQL) — NEVER naive timezone-less `TIMESTAMP` for event/audit timestamps!
- **Multi-Tenant Composite Keys & Soft-Delete Uniqueness:**
  - Include `tenant_id` on every tenant-owned table and lead composite unique/query indexes with `(tenant_id, ...)` so isolation and performance align.
  - When a table uses soft deletes (`deleted_at TIMESTAMPTZ`), a plain `UNIQUE (tenant_id, email)` breaks re-registration after soft delete — use a **partial unique index**: `CREATE UNIQUE INDEX uq_users_tenant_email_active ON users (tenant_id, LOWER(email)) WHERE deleted_at IS NULL;`!
- **Foreign Keys Always Indexed:** PostgreSQL does **NOT** automatically create an index on the referencing (`child`) foreign-key column — unindexed FKs cause sequential scans on parent `DELETE`/`UPDATE` and inflate lock contention!

## 4. Architecture & Implementation
```sql
-- Production-grade multi-tenant table enforcing monetary precision, UTC timestamps, soft-delete uniqueness & FK indexing
CREATE TABLE invoices (
  id             UUID PRIMARY KEY,                     -- UUIDv7 for B-tree locality
  tenant_id      UUID NOT NULL,
  customer_id    UUID NOT NULL,
  invoice_no     TEXT NOT NULL,
  currency       CHAR(3) NOT NULL CHECK (currency ~ '^[A-Z]{3}$'),
  total_minor    BIGINT NOT NULL CHECK (total_minor >= 0),
  status         TEXT NOT NULL CHECK (status IN ('DRAFT', 'ISSUED', 'PAID', 'VOID')),
  version        INTEGER NOT NULL DEFAULT 1 CHECK (version >= 1),
  created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  deleted_at     TIMESTAMPTZ,
  CONSTRAINT fk_invoices_customer FOREIGN KEY (customer_id) REFERENCES customers (id)
);

-- Partial unique index preserves uniqueness for active rows while permitting re-issue after soft delete
CREATE UNIQUE INDEX uq_invoices_tenant_no_active
  ON invoices (tenant_id, invoice_no)
  WHERE deleted_at IS NULL;

-- Always index child foreign key led by tenant_id
CREATE INDEX idx_invoices_tenant_customer
  ON invoices (tenant_id, customer_id);
```

## 5. Platform / Vendor Variations
| Engine | Key Precision / Uniqueness Nuance | Watch-Out |
| :--- | :--- | :--- |
| **PostgreSQL** | Native `TIMESTAMPTZ`, `UUID`, partial `UNIQUE INDEX ... WHERE`, `EXCLUDE USING gist` (non-overlapping date ranges!) | Does NOT auto-index FK child columns |
| **MySQL 8 (InnoDB)** | Clustered PK (`BIGINT` or binary `UUIDv7` — random `UUIDv4` fragments InnoDB B-tree heavily!); `DECIMAL(19,4)` | No partial unique index syntax; use generated column `active_flag` (`1`/`NULL`) in composite `UNIQUE` |
| **SQL Server (MSSQL)** | `DATETIMEOFFSET`, `DECIMAL(19,4)`, filtered `CREATE UNIQUE INDEX ... WHERE deleted_at IS NULL` | Watch implicit `NVARCHAR` vs `VARCHAR` conversion killing index seeks |

## 6. Decision Matrix & Trade-Offs
| Primary Key Type | Index Locality | Distributed / Unpredictable IDs | Verdict |
| :--- | :---: | :---: | :--- |
| **`UUIDv7` (Time-Ordered)** | **High** (sequential inserts) | Yes (safe in public URLs, low fragmentation) | **Recommended modern default** |
| **`BIGINT GENERATED ALWAYS AS IDENTITY`** | Highest (8 bytes) | No (enumerable unless paired with opaque public ID) | Great for high-volume internal fact tables |
| **Random `UUIDv4`** | Poor (random B-tree page splits & WAL bloat) | Yes | Avoid on multi-million-row high-write tables |

## 7. Real Production Scenario
An invoicing app stores `amount FLOAT` and skips `UNIQUE (tenant_id, invoice_no)` relying on `"if (!await findByNo()) insert()"`. Under two concurrent clicks, duplicate invoice numbers commit AND `0.1 + 0.2 = 0.30000000000000004` breaks financial reconciliation. Converting to `BIGINT` minor units, adding `uq_invoices_tenant_no_active`, and handling PG error `23505` cleanly eliminates both defects at the storage layer.

## 8. Failure Modes & Edge Cases
- **WRONG:** Storing money as `FLOAT`/`DOUBLE`, storing comma-separated IDs inside one `TEXT` column, or omitting `FOREIGN KEY` constraints `"because ORM handles it"`.
- **RIGHT:** Enforce normalized relations, `BIGINT`/`NUMERIC` money, `CHECK` constraints, and indexed `FOREIGN KEY`s inside the database.
- **WRONG:** Using `JSONB` as a dumping ground for core relational entities (`orders`, `line_items`, `payments`) that need joins, constraints, and reporting.
- **RIGHT:** Use relational columns for core schema and reserve `JSONB` (with explicit `schema_version`) strictly for genuinely sparse/polymorphic metadata.

## 9. Testing & Verification
- Run `python shadow-db/scripts/sql_migration_safety_verifier.py --check-ddl <schema.sql>` to catch `FLOAT` money columns and unsafe constraints offline.
- Use `shadow_db` MCP `inspect_database_schema` and `generate_dbml_and_erd` on verified local DBs to inspect actual constraints & missing FK indexes.

## 10. Operational Considerations
- Standardize naming conventions across migrations (`pk_`, `fk_`, `uq_`, `chk_`, `idx_`) so constraint violation errors map cleanly to domain error codes in backend handlers.

## 11. Authoritative References
- PostgreSQL Official Documentation — *Data Types, Constraints & Partial Indexes* (`https://www.postgresql.org/docs/current/ddl-constraints.html`).
- IETF RFC 9562 — *UUID Version 7 (Time-Ordered UUIDs)*.

## 12. Limitations & When NOT to Use
- Do NOT over-normalize analytics/warehouse reporting marts into 5NF; OLAP reporting tables intentionally use Kimball Star Schema (`dim_*`/`fact_*`) (`06-backup-pitr-schema-diff-and-dw-etl.md`).
