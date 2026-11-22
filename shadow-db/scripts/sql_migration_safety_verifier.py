#!/usr/bin/env python3
"""Deterministic SQL DDL, Indexing, Lock-Safety & PostgreSQL RLS Verifier (L0/L1 offline CLI).

Zero third-party dependencies (Python 3 stdlib only, read-only SQL analysis).
Validates:
  - Lock-safe DDL checks: lock_timeout, CONCURRENTLY indexes, NOT VALID FKs/checks,
    no destructive DROP/RENAME COLUMN without explicit contract flag, no FLOAT money (--check-ddl)
  - PostgreSQL RLS & SECURITY DEFINER hygiene: (SELECT auth.uid()) initPlan caching,
    SET search_path = '' on SECURITY DEFINER functions (--check-rls)
  - Built-in precision & recall self-test probes (--self-test)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

LOCK_TIMEOUT_RE = re.compile(r"\bSET\s+(?:LOCAL\s+)?lock_timeout\b", re.IGNORECASE)
PLAIN_CREATE_INDEX_RE = re.compile(r"\bCREATE\s+(?:UNIQUE\s+)?INDEX\s+(?!CONCURRENTLY\b)", re.IGNORECASE)
ADD_FK_WITHOUT_NOT_VALID_RE = re.compile(
    r"\bALTER\s+TABLE\b[^;]*\bADD\s+CONSTRAINT\b[^;]*\bFOREIGN\s+KEY\b(?![^;]*\bNOT\s+VALID\b)",
    re.IGNORECASE | re.DOTALL,
)
DROP_OR_RENAME_COL_RE = re.compile(
    r"\bALTER\s+TABLE\b[^;]*\b(?:DROP\s+COLUMN|RENAME\s+COLUMN|ALTER\s+COLUMN[^;]*\bTYPE\b)",
    re.IGNORECASE | re.DOTALL,
)
FLOAT_MONEY_RE = re.compile(
    r"\b(?:amount|price|balance|total|subtotal|fee|tax|salary|cost)[a-z0-9_]*\s+(?:FLOAT\d?|REAL|DOUBLE\s+PRECISION)\b",
    re.IGNORECASE,
)
SEC_DEFINER_RE = re.compile(r"\bSECURITY\s+DEFINER\b", re.IGNORECASE)
SEARCH_PATH_RE = re.compile(r"\bSET\s+search_path\s*=\s*(?:''|\"\"|pg_catalog\s*,\s*pg_temp)", re.IGNORECASE)


def check_ddl(sql_text: str, allow_contract_phase: bool = False) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []

    has_alter_or_index = bool(re.search(r"\b(?:ALTER\s+TABLE|CREATE\s+(?:UNIQUE\s+)?INDEX)\b", sql_text, re.IGNORECASE))
    if has_alter_or_index and not LOCK_TIMEOUT_RE.search(sql_text):
        warnings.append("Missing 'SET lock_timeout' before ALTER TABLE / CREATE INDEX (risk of queueing prod queries behind lock).")

    if PLAIN_CREATE_INDEX_RE.search(sql_text):
        errors.append("Blocking 'CREATE INDEX' detected on existing table; use 'CREATE INDEX CONCURRENTLY' outside a transaction block.")

    if ADD_FK_WITHOUT_NOT_VALID_RE.search(sql_text):
        errors.append(
            "Blocking 'ADD CONSTRAINT ... FOREIGN KEY' without 'NOT VALID' detected (takes SHARE ROW EXCLUSIVE scan). "
            "Use 'ADD CONSTRAINT ... FOREIGN KEY (...) NOT VALID;' followed by 'VALIDATE CONSTRAINT ...;'."
        )

    if not allow_contract_phase and DROP_OR_RENAME_COL_RE.search(sql_text):
        errors.append(
            "Destructive/breaking DDL ('DROP COLUMN', 'RENAME COLUMN', or 'ALTER COLUMN TYPE') detected outside approved Contract phase. "
            "Use Expand -> Backfill -> Switch -> Contract across releases."
        )

    if FLOAT_MONEY_RE.search(sql_text):
        errors.append("Floating-point type (FLOAT/REAL/DOUBLE) used for monetary column; use BIGINT minor units or NUMERIC(18,2).")

    return {"check": "sql_ddl_safety", "passed": len(errors) == 0, "errors": errors, "warnings": warnings}


def check_rls(sql_text: str) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []

    if re.search(r"\bCREATE\s+POLICY\b", sql_text, re.IGNORECASE):
        # Detect uncached auth.uid() / auth.jwt() calls not wrapped in (SELECT auth.uid())
        cleaned = re.sub(r"\(\s*SELECT\s+auth\.(?:uid|jwt)\(\)\s*\)", "", sql_text, flags=re.IGNORECASE)
        if re.search(r"\bauth\.(?:uid|jwt)\(\)", cleaned, re.IGNORECASE):
            errors.append(
                "Uncached 'auth.uid()' or 'auth.jwt()' inside RLS policy (re-evaluated per row!). "
                "Wrap as '(SELECT auth.uid())' to enable PostgreSQL InitPlan single-eval caching."
            )
        if not re.search(r"\bTO\s+(?:authenticated|service_role|[a-z0-9_]+)\b", sql_text, re.IGNORECASE):
            warnings.append("Explicitly scope RLS policy with 'TO authenticated' (avoid accidental public/anon evaluation).")

    if SEC_DEFINER_RE.search(sql_text) and not SEARCH_PATH_RE.search(sql_text):
        errors.append(
            "SECURITY DEFINER function missing \"SET search_path = ''\" (vulnerable to search_path object-shadowing privilege escalation)."
        )

    return {"check": "postgres_rls_security", "passed": len(errors) == 0, "errors": errors, "warnings": warnings}


def run_self_test() -> dict[str, Any]:
    probes: list[tuple[str, bool]] = []

    # PRECISION-1: Lock-safe online DDL with lock_timeout, CONCURRENTLY, NOT VALID + VALIDATE passes
    r1 = check_ddl(
        """
        SET lock_timeout = '3s';
        CREATE INDEX CONCURRENTLY idx_orders_tenant_cust ON orders (tenant_id, customer_id);
        ALTER TABLE orders ADD CONSTRAINT fk_orders_customer FOREIGN KEY (customer_id) REFERENCES customers(id) NOT VALID;
        ALTER TABLE orders VALIDATE CONSTRAINT fk_orders_customer;
        """
    )
    probes.append(("PRECISION-1: Lock-safe CONCURRENTLY index & NOT VALID FK pass", r1["passed"] is True and len(r1["warnings"]) == 0))

    # RECALL-1: Blocking CREATE INDEX and unvalidated FOREIGN KEY rejected
    r2 = check_ddl(
        """
        CREATE INDEX idx_orders_cust ON orders (customer_id);
        ALTER TABLE orders ADD CONSTRAINT fk_orders_cust FOREIGN KEY (customer_id) REFERENCES customers(id);
        """
    )
    probes.append(("RECALL-1: Blocking CREATE INDEX & immediate FK scan rejected", r2["passed"] is False and len(r2["errors"]) >= 2))

    # RECALL-2: Destructive DROP COLUMN / RENAME COLUMN blocked outside Contract phase
    r3 = check_ddl("ALTER TABLE orders DROP COLUMN legacy_total;")
    probes.append(("RECALL-2: Unapproved DROP COLUMN rejected outside Contract phase", r3["passed"] is False))

    # PRECISION-2: DROP COLUMN allowed ONLY when explicit allow_contract_phase=True
    r4 = check_ddl("SET lock_timeout = '2s'; ALTER TABLE orders DROP COLUMN legacy_total;", allow_contract_phase=True)
    probes.append(("PRECISION-2: Contract-phase DROP COLUMN with lock_timeout passes when authorized", r4["passed"] is True))

    # RECALL-3: FLOAT monetary column rejected
    r5 = check_ddl("CREATE TABLE invoices (id UUID PRIMARY KEY, total_amount DOUBLE PRECISION NOT NULL);")
    probes.append(("RECALL-3: DOUBLE PRECISION money column rejected", r5["passed"] is False))

    # PRECISION-3: Cached (SELECT auth.uid()) RLS + hardened SECURITY DEFINER passes
    r6 = check_rls(
        """
        CREATE POLICY tenant_isolation ON orders FOR SELECT TO authenticated
          USING (tenant_id = (SELECT auth.uid()));
        CREATE FUNCTION get_tenant_role() RETURNS TEXT LANGUAGE sql SECURITY DEFINER SET search_path = '' AS $$ SELECT 'viewer'; $$;
        """
    )
    probes.append(("PRECISION-3: Cached (SELECT auth.uid()) RLS & hardened SECURITY DEFINER pass", r6["passed"] is True))

    # RECALL-4: Raw auth.uid() in RLS & SECURITY DEFINER without search_path rejected
    r7 = check_rls(
        """
        CREATE POLICY bad_rls ON orders FOR SELECT USING (user_id = auth.uid());
        CREATE FUNCTION bad_fn() RETURNS VOID LANGUAGE plpgsql SECURITY DEFINER AS $$ BEGIN END; $$;
        """
    )
    probes.append(("RECALL-4: Uncached auth.uid() & unhardened SECURITY DEFINER rejected", r7["passed"] is False and len(r7["errors"]) == 2))

    passed = sum(1 for _, ok in probes if ok)
    return {
        "tool": "sql_migration_safety_verifier.py",
        "total_probes": len(probes),
        "passed": passed,
        "failed": len(probes) - passed,
        "all_passed": passed == len(probes),
        "results": [{"probe": n, "passed": ok} for n, ok in probes],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Offline SQL DDL Lock-Safety, Money Precision & Postgres RLS Verifier")
    parser.add_argument("--self-test", action="store_true", help="Run built-in precision & recall probes")
    parser.add_argument("--check-ddl", metavar="PATH", help="Inspect SQL migration file for lock/breaking/money hazards")
    parser.add_argument("--allow-contract-phase", action="store_true", help="Permit Contract-phase DROP/RENAME DDL")
    parser.add_argument("--check-rls", metavar="PATH", help="Inspect SQL file for Postgres RLS & SECURITY DEFINER safety")
    args = parser.parse_args(argv)

    if args.self_test:
        res = run_self_test()
        print(json.dumps(res, indent=2))
        return 0 if res["all_passed"] else 1
    if args.check_ddl:
        sql = Path(args.check_ddl).read_text(encoding="utf-8")
        res = check_ddl(sql, allow_contract_phase=args.allow_contract_phase)
        print(json.dumps(res, indent=2))
        return 0 if res["passed"] else 1
    if args.check_rls:
        sql = Path(args.check_rls).read_text(encoding="utf-8")
        res = check_rls(sql)
        print(json.dumps(res, indent=2))
        return 0 if res["passed"] else 1

    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
