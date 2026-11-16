---
name: shadow-search
description: "Search, Retrieval & Ranking Engineering. Use when designing or tuning lexical BM25, Indonesian morphology/analyzers, vector ANN, hybrid RRF fusion, cross-encoder reranking, PIT/search_after pagination, zero-downtime alias reindexing, Recall@K/MRR@K/NDCG@K benchmarks, or search tenant ACL prefiltering. Do NOT use for LLM answer faithfulness (shadow-eval), general Redis cache (shadow-cache), or arbitrary SQL tuning (shadow-db)."
---

# `/shadow-search` — Search, Retrieval & Ranking Engineering

- **Owner:** Search pipelines (lexical, vector, hybrid RRF, rerank), analyzer/morphology tuning (Indonesian + English), ranking metrics (`Recall@K`, `MRR@K`, `NDCG@K`), zero-downtime reindex, and tenant ACL prefiltering.
- **Boundaries:** LLM generation faithfulness/red-teaming (`shadow-eval`), Redis key caching (`shadow-cache`), OLTP SQL query tuning (`shadow-db`).

## 1. Preconditions, ACL Safety & Calibration Rules
- **Tenant ACL Prefilter Mandatory:** Filter `tenant_id` and `permission_scopes` **inside** the lexical/vector retrieval query BEFORE top-K scoring and caching — NEVER post-filter top-K results (which leaks existence or returns empty pages) and NEVER return deleted/revoked documents.
- **No Uncalibrated Fixed Thresholds:** Never pick arbitrary fixed cosine similarity cutoffs (e.g., `score > 0.78`) without held-out evaluation curves across languages/slang.

## 2. 7-Step Search Engineering Playbook
Read [`methodologies/HYBRID-BM25-VECTOR-RRF-AND-ACL.md`](methodologies/HYBRID-BM25-VECTOR-RRF-AND-ACL.md) and [`playbooks/SEARCH-RELEVANCE-AND-MIGRATION-PLAYBOOK.md`](playbooks/SEARCH-RELEVANCE-AND-MIGRATION-PLAYBOOK.md):
1. **Characterize Query Tasks:** Separate exact ID/SKU/pasal lookup (lexical BM25) from conceptual semantic queries (dense vector + hybrid RRF).
2. **Design Indonesian + Domain Analyzers:** Handle slang/typo fuzziness, stopwords carefully, stemming vs exact keyword subfields (`keyword` + `text`).
3. **Curate Held-Out Relevance Judgments:** Graded relevance (`0..3`) with Indonesian slang, near-duplicates, and high-selectivity filters.
4. **Measure Baseline (`Recall@K`, `MRR@K`, `NDCG@K`):** Evaluate retrieval independently from LLM answer generation (`/shadow-eval`).
5. **Verify Tenant ACL & Freshness Tombstones:** Test cross-tenant isolation and near-real-time document deletion/revocation.
6. **Tune Hybrid RRF / Rerank Under Latency & Cost Budget:** Compare lexical-only vs vector-only vs RRF ($k=60$) + optional cross-encoder rerank.
7. **Zero-Downtime Alias Reindexing:** Build `index_v2` -> backfill -> verify counts/parity -> atomic alias swap (`index_live`), keeping `index_v1` for instant rollback.

```powershell
python "shadow-search/scripts/search_relevance_acl_gate.py" --self-test
python "shadow-search/scripts/search_relevance_acl_gate.py" --evaluate path/to/search_eval.json
```
