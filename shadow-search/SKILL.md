---
name: shadow-search
description: "Use when tuning search retrieval, BM25, vector ANN, RRF, rank metrics, reindexing, or ACL prefilters. Not for RAG answer grading (/shadow-eval)."
---

# `/shadow-search` — Search, Retrieval & Ranking Engineering

- **Owner:** Search pipelines (lexical BM25, Indonesian + English morphology/analyzers, dense vector ANN, hybrid RRF fusion, cross-encoder reranking), ranking metrics (`Recall@K`, `MRR@K`, `NDCG@K`), zero-downtime alias reindexing, and pre-top-K tenant ACL prefiltering.
- **Boundaries:** LLM answer faithfulness & RAG generation evaluation (`shadow-eval`), agent tool orchestration & prompt caching (`shadow-ai-eng`), Redis key caching (`shadow-cache`), OLTP SQL query tuning (`shadow-db`).

## Reference Guide

Load ONLY the 1–2 modular playbooks needed for the active search subtask:

| Module | Topic | Load When |
| :--- | :--- | :--- |
| [01-search-engines-and-indonesian-analyzers.md](references/01-search-engines-and-indonesian-analyzers.md) | Engine selection (`pgvector`/FTS, Meilisearch, Typesense, OpenSearch, Qdrant), Indonesian/English analyzers, synonyms, fuzziness | Choosing a search engine, fixing Indonesian morphology/stemming/slang, exact SKU/pasal matching |
| [02-hybrid-rrf-chunking-and-reranking.md](references/02-hybrid-rrf-chunking-and-reranking.md) | Structure-aware chunking, BM25 + dense vector RRF fusion, cross-encoder reranking, calibrated cutoffs | Tuning hybrid retrieval quality, chunk boundaries, rerank latency budgets, or removing hardcoded cosine cutoffs |
| [03-pre-top-k-tenant-acl-and-freshness.md](references/03-pre-top-k-tenant-acl-and-freshness.md) | Pre-top-K tenant/scope ACL filtering, near-real-time revocation & tombstones, CDC indexing freshness | Preventing cross-tenant leakage, empty post-filtered pages, or stale revoked document visibility |
| [04-zero-downtime-alias-reindexing-and-benchmarks.md](references/04-zero-downtime-alias-reindexing-and-benchmarks.md) | Blue/green alias reindexing, `PIT` + `search_after` pagination, paired `Recall@K`/`MRR@K`/`NDCG@K` benchmarks | Migrating mappings/embeddings with zero downtime, fixing deep-offset OOM, or evaluating candidate indexes |
| [methodologies/HYBRID-BM25-VECTOR-RRF-AND-ACL.md](methodologies/HYBRID-BM25-VECTOR-RRF-AND-ACL.md) | Core hybrid retrieval & ACL methodology notes | Quick methodological reference on RRF & ACL contracts |
| [playbooks/SEARCH-RELEVANCE-AND-MIGRATION-PLAYBOOK.md](playbooks/SEARCH-RELEVANCE-AND-MIGRATION-PLAYBOOK.md) | Operational relevance & migration checklist | Executing relevance review & index cutover gates |
| [evaluations.md](evaluations.md) | Graded specialist evaluation scenarios (`SRCH-EVAL-01..07`) | Benchmarking retrieval design, ACL safety, and benchmark judgment |

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
python -m unittest discover -s shadow-search/tests -v
```

### Comparing a candidate index with the serving index

Freeze the query set, relevance judgments, permission snapshot, index revisions, K and latency budget before comparing results. Assign stable, unique `query_id` values and a `segment` per query (for example Indonesian exact lookup versus English conceptual search). Export ranked lists for the same identities from both indexes. Supply `tenant_id`, `relevance_grades` (integer grades 0–3 keyed by document ID) and `retrieved` (ordered objects with `id` and `tenant_id`). An empty list records an observed search with no results. If available, pass independent `allowed_document_ids` and `revoked_document_ids` arrays per query. The optional result flag `deleted_or_revoked` is boolean. Keep caller authorization and the ACL snapshot revision alongside the fixture; isolate sensitive relevance data.

Run the evaluator once for each index. Compare only matched query IDs from the same frozen fixture. The generated fallback IDs (`row-1`, etc.) serve single-dataset callers; explicitly name queries for paired analysis. `query_results` shows individual metrics and `segments` gives macro averages and measured/total counts. Repeated documents occupy their actual rank slots, earn gain once, and are counted in `duplicate_hits_at_k`. MRR is the inverse of the first relevant rank. Recall uses distinct positive judgments as denominator. NDCG uses graded gain against ideal order at the same K.

A missing or all-zero judgment set contributes null relevance metrics and makes the gate fail with insufficient evidence. Evaluate intentional no-answer queries as a separate abstention task with its own oracle. A labeled query with an observed empty result gets zero. Invalid data fails before scoring. Unauthorized or revoked results anywhere in the returned list fail the gate; metrics for that query are withheld. A matched tenant and an unflagged document alone cannot establish that the retrieval engine actually applied the permission filter before top-K. Verify query construction and freshness against the owning service.

When the aggregate improves but an important cohort regresses, retain its paired examples, denominators and the owner's tolerance in the decision. Hold promotion while evidence, permissions, or rollback ownership remain unresolved. Hand retrieval scores and ACL findings to `shadow-eval` separately from answer accuracy. An evaluator PASS covers the configured fixture and threshold. The incident/release owner decides rollout under the project's established workflow.
