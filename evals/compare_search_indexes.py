"""Compare two frozen search/RAG traces against the same labeled queries and ACL snapshot."""
import argparse
import json
from pathlib import Path
import runpy
import sys

ROOT = Path(__file__).resolve().parents[1]
score_search = runpy.run_path(str(ROOT / "shadow-search/scripts/search_relevance_acl_gate.py"))["evaluate_search_dataset"]
score_answers = runpy.run_path(str(ROOT / "shadow-eval/scripts/ai_eval_gate.py"))["score_rag_dataset"]


def identifier(value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Expected a nonempty string identifier.")
    return value


def ids(values):
    if not isinstance(values, list):
        raise ValueError("Expected an ordered array of document IDs.")
    return [identifier(item) for item in values]


def build_run(fixture, run):
    queries = fixture["queries"]
    catalog = fixture["documents"]
    for key in ("acl_revision", "corpus_revision", "judgment_revision"):
        if fixture[key] != run[key]:
            raise ValueError(f"Trace revision mismatch: {key}")
    rows = run["results"]
    if not isinstance(rows, dict) or rows.keys() != queries.keys():
        raise ValueError("Both indexes must report exactly the frozen query IDs.")
    search_queries, samples, violations = [], [], []
    for query_id, query in queries.items():
        tenant = identifier(query["tenant_id"])
        segment = identifier(query["segment"])
        allowed = set(ids(query["allowed_document_ids"]))
        grades = query["relevance_grades"]
        result = rows[query_id]
        ranking = ids(result["ranking"])
        context = ids(result["context"])
        if not set(context).issubset(ranking):
            violations.append({"query_id": query_id, "reason": "context_outside_retrieval"})
        for doc_id in set(context + ranking) | allowed | set(grades):
            if doc_id not in catalog:
                raise ValueError(f"Document outside frozen corpus in {query_id}.")
        def chunk(doc_id):
            doc = catalog[doc_id]
            return {"id": doc_id, "tenant_id": identifier(doc["tenant_id"]),
                    "deleted_or_revoked": doc["revoked"]}
        reviewed_claims = query["reviewed_claims"]
        if not isinstance(reviewed_claims, dict) or not isinstance(result["claims"], list):
            raise ValueError("Claims and their independent judgments are required.")
        claims = []
        for claim in result["claims"]:
            statement = identifier(claim["claim"])
            references = ids(claim["citations"])
            attested = set(ids(reviewed_claims.get(statement, [])))
            claims.append({"claim": statement, "citations": references,
                           "supported": bool(references) and set(references) <= attested})
        for doc_id in context:
            doc = catalog[doc_id]
            if doc_id not in allowed or doc["revoked"] or doc["tenant_id"] != tenant:
                violations.append({"query_id": query_id, "reason": "unauthorized_context"})
        search_queries.append({"query_id": query_id, "segment": segment, "tenant_id": tenant,
                               "allowed_document_ids": sorted(allowed), "relevance_grades": grades,
                               "retrieved": [chunk(doc_id) for doc_id in ranking]})
        samples.append({"sample_type": "answerable", "sample_id": query_id, "language": segment,
                        "tenant_id": tenant, "expected_chunk_ids": [d for d, g in grades.items() if g > 0],
                        "retrieved_chunks": [chunk(d) for d in context],
                        "answer_citations": result["citations"], "abstained": result["abstained"],
                        "claims": claims})
    return {"revision": identifier(run["revision"]), "search": score_search({
        "queries": search_queries, "k": fixture["k"], "min_ndcg": fixture["min_ndcg"]}),
        "answers": score_answers(samples), "violations": violations}


def compare(fixture, acl_revision):
    if identifier(fixture["acl_revision"]) != identifier(acl_revision):
        return {"decision": "HOLD", "reasons": ["stale_acl_snapshot"]}
    corpus = identifier(fixture["corpus_revision"])
    labels = identifier(fixture["judgment_revision"])
    if not all(isinstance(fixture[field], dict) and fixture[field] for field in ("documents", "queries")):
        raise ValueError("Frozen corpus and queries must be nonempty mappings.")
    if fixture["baseline"]["revision"] == fixture["candidate"]["revision"]:
        raise ValueError("Index revisions must be distinct.")
    for doc in fixture["documents"].values():
        if not isinstance(doc, dict) or type(doc.get("revoked")) is not bool:
            raise ValueError("Each corpus document needs an explicit boolean revocation status.")
        identifier(doc["tenant_id"])
    for query in fixture["queries"].values():
        grades = query["relevance_grades"]
        if not isinstance(grades, dict) or any(type(g) is not int or not 0 <= g <= 3 for g in grades.values()):
            raise ValueError("Relevance labels must be a mapping of document IDs to grades 0..3.")
        if any(g > 0 and (d not in query["allowed_document_ids"] or d not in fixture["documents"]
                          or fixture["documents"][d]["revoked"]
                          or fixture["documents"][d]["tenant_id"] != query["tenant_id"]) for d, g in grades.items()):
            raise ValueError("Positive labels conflict with the frozen ACL or corpus.")
    base, candidate = (build_run(fixture, fixture[side]) for side in ("baseline", "candidate"))
    # Compare both sides of the retrieval-to-generation handoff for each cohort.
    reasons = []
    if not candidate["search"]["valid"] or not candidate["answers"]["gate_passed"] or candidate["violations"]:
        reasons.append("candidate_gate_failed")
    if (base["search"].get("evidence_status") != "MEASURED" or base["violations"]
            or base["answers"].get("errors")):
        reasons.append("baseline_unusable_for_paired_comparison")
    paired = {}
    old = base["search"].get("query_results", [])
    new = candidate["search"].get("query_results", [])
    for a, b in zip(old, new):
        if a["query_id"] != b["query_id"]:
            raise ValueError("Unpaired query results.")
        delta = None
        if a["ndcg_at_k"] is not None and b["ndcg_at_k"] is not None:
            delta = round(b["ndcg_at_k"] - a["ndcg_at_k"], 6)
        paired[a["query_id"]] = {"segment": a["segment"], "ndcg_delta": delta}
    minimum = fixture["min_queries_per_segment"]
    if type(minimum) is not int or minimum < 1:
        raise ValueError("min_queries_per_segment must be a positive integer.")
    segments = {}
    for segment in {q["segment"] for q in fixture["queries"].values()}:
        deltas = [q["ndcg_delta"] for q in paired.values()
                  if q["segment"] == segment and q["ndcg_delta"] is not None]
        mean = sum(deltas) / len(deltas) if deltas else None
        if len(deltas) < minimum:
            reasons.append(f"insufficient_pairs:{segment}")
        if mean is not None and mean < 0:
            reasons.append(f"segment_regression:{segment}")
        answer_deltas = {}
        prior = base["answers"]["by_language"].get(segment, {})
        current = candidate["answers"]["by_language"].get(segment, {})
        for metric in ("context_recall", "citation_integrity", "claim_support"):
            before, after = prior.get(metric), current.get(metric)
            change = None if before is None or after is None else after - before
            if before is not None and (after is None or after < before):
                reasons.append(f"answer_regression:{segment}:{metric}")
            answer_deltas[metric] = change
        segments[segment] = {"paired_count": len(deltas), "mean_ndcg_delta": mean,
                             "answer_deltas": answer_deltas}
    return {"decision": "HOLD" if reasons else "ELIGIBLE_FOR_REVIEW", "reasons": sorted(reasons),
            "corpus_revision": corpus, "judgment_revision": labels, "acl_revision": acl_revision,
            "baseline": base, "candidate": candidate, "pairs": paired, "segments": segments}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("fixture", type=Path)
    parser.add_argument("--acl-revision", required=True, help="Current revision from the policy owner")
    args = parser.parse_args()
    try:
        result = compare(json.loads(args.fixture.read_text(encoding="utf-8-sig")), args.acl_revision)
    except (ValueError, TypeError, KeyError, OSError, AttributeError) as error:
        result = {"decision": "HOLD", "reasons": ["invalid_input"], "error": str(error)}
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["decision"] == "ELIGIBLE_FOR_REVIEW" else 1


if __name__ == "__main__":
    sys.exit(main())
