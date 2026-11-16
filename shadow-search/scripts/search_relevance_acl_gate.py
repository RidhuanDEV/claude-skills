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
    scores: dict[str, float] = {}
    for rlist in ranked_lists:
        for rank, doc_id in enumerate(rlist, start=1):
            scores[doc_id] = scores.get(doc_id, 0.0) + (1.0 / (k + rank))
    return [doc_id for doc_id, _ in sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))]


def evaluate_search_dataset(spec: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(spec, dict) or not spec.get("queries"):
        return {"status": "FAIL", "valid": False, "errors": ["Search evaluation dataset requires non-empty 'queries'."]}

    top_k = max(1, int(spec.get("k", 5)))
    min_ndcg = float(spec.get("min_ndcg", 0.70))
    errors: list[str] = []

    if spec.get("uses_uncalibrated_fixed_similarity_threshold"):
        errors.append("Uncalibrated fixed similarity threshold used without held-out evaluation curve.")

    recall_list: list[float] = []
    mrr_list: list[float] = []
    ndcg_list: list[float] = []
    acl_leaks = 0
    revoked_leaks = 0

    for q in spec["queries"]:
        req_tenant = str(q.get("tenant_id", ""))
        rel_grades: dict[str, int] = {str(k): int(v) for k, v in q.get("relevance_grades", {}).items()}
        retrieved = q.get("retrieved", [])[:top_k]

        for doc in retrieved:
            if req_tenant and str(doc.get("tenant_id", "")) != req_tenant:
                acl_leaks += 1
            if doc.get("deleted_or_revoked"):
                revoked_leaks += 1

        # Recall@K
        total_rel = sum(1 for g in rel_grades.values() if g > 0)
        hits = sum(1 for doc in retrieved if rel_grades.get(str(doc.get("id")), 0) > 0)
        recall_list.append(hits / total_rel if total_rel > 0 else 1.0)

        # MRR@K
        rr = 0.0
        for idx, doc in enumerate(retrieved, start=1):
            if rel_grades.get(str(doc.get("id")), 0) > 0:
                rr = 1.0 / idx
                break
        mrr_list.append(rr)

        # NDCG@K
        dcg = 0.0
        for idx, doc in enumerate(retrieved, start=1):
            g = rel_grades.get(str(doc.get("id")), 0)
            if g > 0:
                dcg += (2 ** g - 1) / math.log2(idx + 1)
        ideal_grades = sorted((g for g in rel_grades.values() if g > 0), reverse=True)[:top_k]
        idcg = sum((2 ** g - 1) / math.log2(idx + 1) for idx, g in enumerate(ideal_grades, start=1))
        ndcg_list.append(dcg / idcg if idcg > 0 else 1.0)

    avg_recall = round(sum(recall_list) / len(recall_list), 4)
    avg_mrr = round(sum(mrr_list) / len(mrr_list), 4)
    avg_ndcg = round(sum(ndcg_list) / len(ndcg_list), 4)

    if acl_leaks > 0:
        errors.append(f"CRITICAL ACL violation: {acl_leaks} cross-tenant document(s) leaked in search results.")
    if revoked_leaks > 0:
        errors.append(f"Freshness/ACL violation: {revoked_leaks} deleted/revoked document(s) returned.")
    if avg_ndcg < min_ndcg:
        errors.append(f"NDCG@{top_k} ({avg_ndcg}) below required baseline ({min_ndcg}).")

    return {
        "skill_id": "shadow-search",
        "status": "PASS" if not errors else "FAIL",
        "valid": len(errors) == 0,
        "k": top_k,
        "recall_at_k": avg_recall,
        "mrr_at_k": avg_mrr,
        "ndcg_at_k": avg_ndcg,
        "acl_leaks": acl_leaks,
        "revoked_leaks": revoked_leaks,
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
        spec = json.loads(Path(args.evaluate).read_text(encoding="utf-8"))
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
