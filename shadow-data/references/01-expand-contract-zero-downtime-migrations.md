# 01. Expand-Contract Zero-Downtime Migrations

## 1. Purpose & Activation Conditions
Evolve live production schemas across rolling deployments with **zero downtime** and **zero mixed-version writer crashes** using the 4-phase **Expand -> Backfill -> Switch -> Contract** pattern. Load before renaming columns, changing data types, splitting/merging tables, or enforcing new `NOT NULL` constraints on live services.

## 2. Prerequisites
- Versioned migration pipeline, ability to observe old vs new app release telemetry, and explicit `L4` Monarch approval before running any Contract/destructive DDL on staging/prod.

## 3. Technical Principles & Constraints
- **Why Single-Step Breaking DDL Causes Outages:** During rolling Kubernetes/PM2 deployments, **Release N (old code)** and **Release N+1 (new code)** execute simultaneously against the **exact same database**! Dropping or renaming a column in Release N+1 immediately crashes all running Release N pods AND makes rollback impossible!
- **Mandatory 4-Phase Gate Matrix:**
  1. **Phase 1 — Expand (Additive Only, Safe Rollback):** Add new nullable columns/tables/concurrent indexes compatible with BOTH Release N and Release N+1. Deploy Release N+1 writing to **both** old and new columns (`dual-write`, or DB trigger when multiple independent legacy writers exist!). Verify rollback to Release N works cleanly.
  2. **Phase 2 — Backfill (Resumable & Throttled):** Populate historical rows via idempotent keyset-chunked batches (`03`), verifying concurrent legacy writers cannot corrupt rows behind the completed cursor (`test_expand_backfill.py`). Reconcile `100%` row counts and values!
  3. **Phase 3 — Switch Reads:** Flip Release N+2 (or feature flag) to read from the new representation while still keeping the old column populated temporarily for instant read fallback. Monitor parity and error rates over a full business cycle.
  4. **Phase 4 — Contract (Separate Release + Separate `L4` Approval):** Inventory EVERY reader, writer, ETL job, BI dashboard, and rollback image. Retire/drop the old column ONLY after telemetry confirms **`0` legacy accesses**, retention window passes, and Monarch approves destructive `L4` DDL!
- **Ephemeral Verification Container Cleanup (`Rule #23 & #29`):** When verifying migrations in local Docker Postgres/MySQL containers, ALWAYS pass `--rm --label shadow.ephemeral=true` and tear down inside `try/finally` (`docker rm -f -v` / `docker compose down -v --rmi local --remove-orphans`).

## 4. Architecture & Implementation
```sql
-- PHASE 1 (EXPAND): Safe additive column + trigger keeping mixed-version legacy writers synchronized
SET lock_timeout = '3s';
SET statement_timeout = '30s';

ALTER TABLE orders ADD COLUMN IF NOT EXISTS total_minor BIGINT;

CREATE OR REPLACE FUNCTION sync_orders_total_minor() RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
  IF NEW.total_minor IS NULL AND NEW.legacy_total_decimal IS NOT NULL THEN
    NEW.total_minor := ROUND(NEW.legacy_total_decimal * 100)::BIGINT;
  END IF;
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_orders_sync_total_minor ON orders;
CREATE TRIGGER trg_orders_sync_total_minor
  BEFORE INSERT OR UPDATE ON orders
  FOR EACH ROW EXECUTE FUNCTION sync_orders_total_minor();
```
Offline migration phase gate check:
```powershell
python "shadow-data/scripts/data_migration_plan_verifier.py" --self-test
python "shadow-data/scripts/data_migration_plan_verifier.py" --check-migration-phases path/to/phases.json
python -m unittest discover -s "shadow-data/tests" -v
```

## 5. Platform / Vendor Variations
| Migration Operation | Expand-Contract Safe Sequence | Never Do in 1 Step |
| :--- | :--- | :--- |
| **Rename Column (`name -> full_name`)** | Add `full_name` -> dual-write/trigger + backfill -> switch reads -> drop `name` later | `ALTER TABLE RENAME COLUMN` |
| **Change Type (`INT -> BIGINT` / `VARCHAR -> UUID`)** | Add new typed column -> dual-write + backfill -> swap reads -> drop old column | `ALTER COLUMN TYPE` (rewrites entire table under `ACCESS EXCLUSIVE` lock!) |
| **Add `NOT NULL` Constraint** | Add `CHECK (col IS NOT NULL) NOT VALID` -> backfill -> `VALIDATE CONSTRAINT` -> `SET NOT NULL` (PG 12+) | `ALTER COLUMN SET NOT NULL` directly on unvalidated 50M-row table |

## 6. Decision Matrix & Trade-Offs
| Dual-Write Mechanism | Handles External Legacy Writers? | Cleanup Effort | Choose When |
| :--- | :---: | :---: | :--- |
| **App-Level Dual-Write** | No (only your upgraded service) | Low (remove in Switch+1) | Single microservice owns the table exclusively |
| **DB `BEFORE INSERT/UPDATE` Trigger** | **YES (handles ALL legacy writers!)** | Medium (drop trigger in Contract) | Multiple services, legacy cron jobs, or rolling pods write concurrently |

## 7. Real Production Scenario
An e-commerce team migrates `orders.amount` (`NUMERIC`) to `orders.amount_minor` (`BIGINT`) by running `ALTER TABLE orders ALTER COLUMN amount TYPE BIGINT` during a Tuesday deploy. PostgreSQL acquires an `ACCESS EXCLUSIVE` lock rewriting 18M rows for 6 minutes, returning `503` across the entire storefront, and rolling pods crash because ORM models expect decimal values. Switching to the 4-phase Expand-Contract trigger + chunked backfill eliminates both lock downtime and mixed-version crashes.

## 8. Failure Modes & Edge Cases
- **WRONG:** Proceeding straight to Phase 4 (`DROP COLUMN`) because `"our app PR removed all references"`, forgetting a nightly BI Pentaho/Airflow job still selects the old column!
- **RIGHT:** Audit query logs (`pg_stat_statements`), ETL/BI consumers, and rollback images; hold Contract whenever any external consumer status is unknown.
- **WRONG:** Leaving stopped `*-migration-verification` Docker containers and orphan volumes behind after local test runs.
- **RIGHT:** Always wrap ephemeral verification containers with `--rm --label shadow.ephemeral=true` and deterministic `try/finally` teardown.

## 9. Testing & Verification
- Run `python -m unittest discover -s shadow-data/tests -v` (`test_expand_backfill.py` proves mixed-version legacy writer invalidation detection + `test_data_migration_plan_verifier.py`).
- Test BOTH forward migration AND rolling back the application code to Release N against the Expanded schema before deploying!

## 10. Operational Considerations
- Keep Expand-to-Contract transitions tracked with a follow-up ticket + owner + target retirement date so dual columns never linger forgotten for years.

## 11. Authoritative References
- Martin Fowler / Pramod Sadalage — *Evolutionary Database Design & Expand-Contract Pattern* (`https://martinfowler.com/bliki/ParallelChange.html`).
- PostgreSQL Documentation — *ALTER TABLE Locking & `NOT VALID` Constraints* (`https://www.postgresql.org/docs/current/sql-altertable.html`).

## 12. Limitations & When NOT to Use
- For brand-new greenfield tables with zero live production rows or zero existing readers, a direct additive `CREATE TABLE` needs no 4-phase Expand-Contract ceremony.
