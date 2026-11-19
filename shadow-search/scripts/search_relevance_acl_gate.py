#!/usr/bin/env python3
"""
Shadow Search Relevance & Tenant ACL Gate (search_relevance_acl_gate.py)

Deterministic evaluator computing Recall@K, MRR@K, NDCG@K, Reciprocal Rank Fusion (RRF),
and verifying zero cross-tenant ACL leakage and deleted/revoked document exclusion.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any


def reciprocal_rank_fusion(ranked_lists: list[list[str]], k: int = 60) -> list[str]:
    if type(k) is not int or k < 0:
        raise ValueError("RRF k must be a non-negative integer.")
    scores: dict[str, float] = {}
    for ranked in ranked_lists:
        seen: set[str] = set()
        for rank, doc_id in enumerate(ranked, start=1):
            if doc_id not in seen:
                scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank)
                seen.add(doc_id)
    return sorted(scores, key=lambda doc_id: (-scores[doc_id], doc_id))


METRICS = ("recall_at_k", "mrr_at_k", "ndcg_at_k")


def identifier(value: object) -> bool:
    return (isinstance(value, str) and bool(value.strip())) or type(value) is int


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    measured = [row for row in rows if row["ndcg_at_k"] is not None]
    return {
        "total_queries": len(rows),
        "measured_queries": len(measured),
        **{metric: round(sum(row[metric] for row in measured) / len(measured), 4)
           if measured else None for metric in METRICS},
    }


def snapshot_ids(query: dict[str, Any], field: str) -> set[str] | None:
    if field not in query:
        return None
    ids = query[field]
    if not isinstance(ids, list) or not all(identifier(item) for item in ids):
        raise ValueError(f"{field} must be an array of document IDs.")
    return set(map(str, ids))


def evaluate_query(query: object, position: int, k: int) -> dict[str, Any]:
    if not isinstance(query, dict):
        raise ValueError("query must be an object.")
    grades = query.get("relevance_grades", {})
    if not isinstance(grades, dict) or not all(
        identifier(key) and type(value) is int and 0 <= value <= 3 for key, value in grades.items()
    ):
        raise ValueError("relevance_grades must map document IDs to integers 0..3.")
    grades = {str(key): value for key, value in grades.items()}
    query_id = query.get("query_id", f"row-{position}")
    segment = query.get("segment", "(unsegmented)")
    if not all(isinstance(value, str) and value.strip() for value in (query_id, segment)):
        raise ValueError("query_id and segment must be non-empty strings.")
    tenant = query.get("tenant_id")
    documents = query.get("retrieved")
    if not identifier(tenant):
        raise ValueError("tenant_id is required for isolation checks.")
    if not isinstance(documents, list):
        raise ValueError("retrieved must be an array; use [] for a search returning no results.")
    allowed = snapshot_ids(query, "allowed_document_ids")
    revoked = snapshot_ids(query, "revoked_document_ids") or set()
    seen: set[str] = set()
    hits = duplicates = acl_leaks = revoked_leaks = 0
    reciprocal_rank = dcg = 0.0
    for rank, doc in enumerate(documents, start=1):
        if not isinstance(doc, dict) or not identifier(doc.get("id")) or not identifier(doc.get("tenant_id")):
            raise ValueError(f"retrieved[{rank - 1}] requires a document ID and tenant ID.")
        flag = doc.get("deleted_or_revoked", False)
        if type(flag) is not bool:
            raise ValueError(f"retrieved[{rank - 1}].deleted_or_revoked must be boolean.")
        doc_id = str(doc["id"])
        if str(doc["tenant_id"]) != str(tenant) or (allowed is not None and doc_id not in allowed):
            acl_leaks += 1
        if flag or doc_id in revoked:
            revoked_leaks += 1
        if rank > k:
            continue
        if doc_id in seen:
            duplicates += 1
            continue
        seen.add(doc_id)
        grade = grades.get(doc_id, 0)
        if grade:
            hits += 1
            if hits == 1:
                reciprocal_rank = 1.0 / rank
            dcg += (2 ** grade - 1) / math.log2(rank + 1)

    positive = sorted((g for g in grades.values() if g > 0), reverse=True)
    metrics = dict.fromkeys(METRICS)
    if acl_leaks or revoked_leaks:
        reason = "ACCESS_VIOLATION"
    elif not positive:
        reason = "NO_POSITIVE_JUDGMENTS" if grades else "MISSING_JUDGMENTS"
    else:
        ideal = sum((2 ** grade - 1) / math.log2(rank + 1)
                    for rank, grade in enumerate(positive[:k], start=1))
        metrics = dict(zip(METRICS, (hits / len(positive), reciprocal_rank, dcg / ideal)))
        reason = "MEASURED"
    return {
        "query_id": query_id, "segment": segment, "evidence_status": reason,
        "duplicate_hits_at_k": duplicates, "acl_leaks": acl_leaks,
        "revoked_leaks": revoked_leaks, **metrics,
    }


def invalid_result(message: str) -> dict[str, Any]:
    return {"skill_id": "shadow-search", "status": "FAIL", "valid": False,
            "evidence_status": "INVALID_INPUT", "errors": [message]}


def evaluate_search_dataset(spec: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(spec, dict) or not isinstance(spec.get("queries"), list) or not spec["queries"]:
        return invalid_result("Search evaluation requires a non-empty array of queries.")
    k = spec.get("k", 5)
    threshold = spec.get("min_ndcg", 0.70)
    uncalibrated = spec.get("uses_uncalibrated_fixed_similarity_threshold", False)
    if type(k) is not int or k < 1:
        return invalid_result("k must be a positive integer.")
    if type(threshold) not in (float, int) or not 0 <= threshold <= 1:
        return invalid_result("min_ndcg must be a finite number in [0, 1].")
    if type(uncalibrated) is not bool:
        return invalid_result("uses_uncalibrated_fixed_similarity_threshold must be boolean.")

    rows = []
    segments: dict[str, list[dict[str, Any]]] = {}
    query_ids: set[str] = set()
    for pos, query in enumerate(spec["queries"]):
        try:
            row = evaluate_query(query, pos + 1, k)
        except ValueError as error:
            return invalid_result(f"queries[{pos}]: {error}")
        if row["query_id"] in query_ids:
            return invalid_result(f"queries[{pos}]: query_id must be unique.")
        query_ids.add(row["query_id"])
        rows.append(row)
        segments.setdefault(row["segment"], []).append(row)

    summary = summarize(rows)
    acl_leaks = sum(row["acl_leaks"] for row in rows)
    revoked_leaks = sum(row["revoked_leaks"] for row in rows)
    errors: list[str] = []
    if acl_leaks:
        errors.append(f"ACL violation: {acl_leaks} unauthorized result(s).")
    if revoked_leaks:
        errors.append(f"Freshness violation: {revoked_leaks} revoked/deleted result(s).")
    if uncalibrated:
        errors.append("Uncalibrated fixed similarity threshold without a held-out evaluation curve.")
    missing = sum(row["evidence_status"] in ("MISSING_JUDGMENTS", "NO_POSITIVE_JUDGMENTS") for row in rows)
    if missing:
        errors.append(f"{missing} query or queries lack positive held-out judgments.")
    measured = [row["ndcg_at_k"] for row in rows if row["ndcg_at_k"] is not None]
    if measured and sum(measured) / len(measured) < threshold:
        errors.append(f"NDCG@{k} below required baseline {threshold}.")
    return {
        "skill_id": "shadow-search", "status": "FAIL" if errors else "PASS",
        "valid": not errors, "k": k, **summary,
        "evidence_status": "MEASURED" if len(measured) == len(rows) else "INSUFFICIENT_EVIDENCE",
        "acl_leaks": acl_leaks, "revoked_leaks": revoked_leaks,
        "query_results": rows, "segments": {name: summarize(group) for name, group in segments.items()},
        "errors": errors,
    }


def run_self_test() -> dict[str, Any]:
    results: list[dict[str, Any]] = []

    golden = {
        "k": 3,
        "min_ndcg": 0.75,
        "queries": [
            {
                "query": "cara bayar pajak telat",
                "tenant_id": "t_a",
                "relevance_grades": {"d1": 3, "d2": 1},
                "retrieved": [
                    {"id": "d1", "tenant_id": "t_a", "deleted_or_revoked": False},
                    {"id": "d2", "tenant_id": "t_a", "deleted_or_revoked": False},
                ],
            }
        ],
    }
    res_ok = evaluate_search_dataset(golden)
    results.append({"probe": "PRECISION-1: Held-out NDCG@3=1.0 & 0 ACL/revoked leaks pass", "passed": res_ok["valid"] and res_ok["ndcg_at_k"] == 1.0})

    # §10.1 Must-fail: Tenant B sees Tenant A's document
    leak = json.loads(json.dumps(golden))
    leak["queries"][0]["tenant_id"] = "t_b"
    results.append({"probe": "MUST-FAIL-1 (§10.1): Blocks cross-tenant document leak (Tenant B sees Tenant A result)", "passed": not evaluate_search_dataset(leak)["valid"]})

    # Deleted/revoked doc still returned
    revoked = json.loads(json.dumps(golden))
    revoked["queries"][0]["retrieved"][0]["deleted_or_revoked"] = True
    results.append({"probe": "RECALL-1: Blocks deleted or permission-revoked document in results", "passed": not evaluate_search_dataset(revoked)["valid"]})

    # RRF fusion correctness property: doc ranked #1 in both lists beats doc ranked #2 in one list
    fused = reciprocal_rank_fusion([["d1", "d2"], ["d1", "d3"]], k=60)
    results.append({"probe": "PRECISION-2: RRF fusion ranks consensus top document first", "passed": fused[0] == "d1"})

    results.append({"probe": "BOUNDARY-1: Rejects empty dataset gracefully", "passed": not evaluate_search_dataset({})["valid"]})
    results.append({"probe": "PRECISION-3: Deterministic repeat evaluation", "passed": evaluate_search_dataset(golden) == res_ok})

    passed = sum(1 for r in results if r["passed"])
    return {
        "tool": "search_relevance_acl_gate.py",
        "total_probes": len(results),
        "passed": passed,
        "failed": len(results) - passed,
        "all_passed": passed == len(results),
        "results": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Shadow Search Relevance & ACL Gate")
    parser.add_argument("--evaluate", default=None, help="JSON search evaluation dataset")
    parser.add_argument("--out", default=None, help="Optional output file path")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        out_data = run_self_test()
        exit_code = 0 if out_data["all_passed"] else 1
    elif args.evaluate:
        try:
            spec = json.loads(Path(args.evaluate).read_text(encoding="utf-8-sig"))
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            out_data = invalid_result(f"Could not read evaluation JSON ({type(error).__name__}).")
        else:
            out_data = evaluate_search_dataset(spec)
        exit_code = 0 if out_data["valid"] else 1
    else:
        parser.print_help()
        return 0

    rendered = json.dumps(out_data, indent=2)
    if args.out:
        Path(args.out).write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
