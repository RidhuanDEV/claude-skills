# 04. Zero-Downtime Alias Reindexing, Deep Pagination & Benchmarks

## 1. Purpose & Activation Conditions
Execute zero-downtime search index migrations via atomic alias swaps, support stable deep pagination (`PIT` + `search_after`), and run paired relevance benchmarks (`Recall@K`, `MRR@K`, `NDCG@K`) segmented by language and query cohort. Load when reindexing schemas/embeddings or gating a candidate search index against the live serving index.

## 2. Prerequisites
- Frozen labeled relevance fixture (`0..3` graded relevance per query, segmented by cohort + frozen ACL snapshot revision) and `search_relevance_acl_gate.py`.

## 3. Technical Principles & Constraints
- **Zero-Downtime Atomic Alias Reindexing Protocol (Never Mutate Live Mappings!):**
  1. Never point application code directly at a concrete index name (`docs_v1`) — always query a logical read alias (`docs_live`)!
  2. To change analyzers, chunking, or embedding models: create `docs_v2` with the new mapping/dimensions, enable dual-write (or CDC/outbox replay from watermark) into `docs_v2`, backfill all historical documents cleanly,
  3. Verify document counts, `0` ACL leaks, and paired benchmark parity (`docs_v2` >= `docs_v1` across ALL key segments!),
  4. Execute a single atomic alias swap (`remove docs_live from docs_v1` + `add docs_live to docs_v2` in one API call) — keeping `docs_v1` warm for `24–72 hours` for instant `< 1s` rollback if latency or relevance dips!
- **Deep Pagination (`PIT` + `search_after`, NEVER `from: 50000`):** Standard `from + size` pagination in Elasticsearch/OpenSearch forces every shard to allocate and sort `from + size` hits (`max_result_window = 10,000` ceiling, causes OOM!). Use a **Point-in-Time (`PIT`)** snapshot paired with **`search_after`** tie-broken by unique `_id` for consistent deep pagination!
- **Paired Candidate vs Serving Index Evaluation Discipline:**
  - Freeze **query set (unique stable `query_id`s + `segment` tags)**, **graded relevance judgments (`0–3`)**, **ACL policy snapshot revision**, **K**, and **latency budget** identically across both runs!
  - Evaluate **intentional no-answer queries** separately as an abstention task (missing/all-zero judgments fail the relevance gate with insufficient evidence!).
  - Inspect **per-segment regressions** (`id_exact_lookup` vs `en_conceptual` vs `id_slang`) — NEVER promote an index whose aggregate NDCG rose `+3%` while exact Indonesian SKU/pasal lookup dropped `-12%`!
  - Hand retrieval scores (`Recall@K`, `MRR@K`, `NDCG@K`, `duplicate_hits_at_k`, ACL results) cleanly to `/shadow-eval` separately from LLM answer faithfulness!

## 4. Architecture & Implementation
Atomic Zero-Downtime Alias Swap (OpenSearch / Elasticsearch):
```json
POST /_aliases
{
  "actions": [
    { "remove": { "index": "docs_v1", "alias": "docs_live" } },
    { "add":    { "index": "docs_v2", "alias": "docs_live" } }
  ]
}
```
Offline paired search benchmark & ACL verification CLI (`L0`/`L1`):
```powershell
python "shadow-search/scripts/search_relevance_acl_gate.py" --self-test
python "shadow-search/scripts/search_relevance_acl_gate.py" --evaluate path/to/serving_v1.json
python "shadow-search/scripts/search_relevance_acl_gate.py" --evaluate path/to/candidate_v2.json
python "evals/compare_search_indexes.py" --help
```

## 5. Platform / Vendor Variations
| Search Platform | Zero-Downtime Reindex Pattern | Deep Pagination Pattern |
| :--- | :--- | :--- |
| **OpenSearch / Elasticsearch** | `docs_v1 -> docs_v2` + atomic `/_aliases` swap | `POST /_pit` + `search_after` (always close PIT when done!) |
| **PostgreSQL (`pgvector` / `tsvector`)** | Add `embedding_v2` column -> keyset backfill -> `CREATE INDEX CONCURRENTLY` -> switch query -> Contract (`shadow-data`) | Keyset cursor `(score, id)` (`shadow-api` Module `03`) |
| **Qdrant / Meilisearch / Typesense** | Collection aliases (`update_aliases` atomic swap) | Keyset/scroll cursor (`next_page_offset`) |

## 6. Decision Matrix & Trade-Offs (Core Retrieval Metrics)
| Metric | Formula Intuition | Best Diagnostic Role |
| :--- | :--- | :--- |
| **`Recall@K`** | Fraction of all relevant docs retrieved in top `K` | **Primary RAG gate** (if missing from top-K, LLM can NEVER cite it!) |
| **`MRR@K`** | `1 / rank_of_first_relevant_doc` | Exact lookup / navigational search (SKU, pasal, FAQ) |
| **`NDCG@K`** | Graded (`0..3`) position-discounted ranking quality | Multi-result relevance ranking & reranker tuning |
| **`duplicate_hits_at_k`** | Repeated `doc_id`s occupying top-K slots | Detects broken chunk deduplication wasting LLM context budget |

## 7. Real Production Scenario
A team migrates from `ada-002` to a newer multilingual embedding model. Overall `NDCG@10` improves from `0.74 -> 0.79`, so they plan to drop `docs_v1` immediately. Running paired per-segment analysis via `search_relevance_acl_gate.py` exposes a hidden `-15%` regression on the `id_exact_code` segment (missing boosted keyword subfield in `docs_v2` mapping!). Fixing the mapping on `docs_v3`, verifying all segments improve with `0` ACL violations, swapping `docs_live` atomically, and retaining `docs_v1` for 48h enables a zero-incident launch.

## 8. Failure Modes & Edge Cases
- **WRONG:** Dropping `docs_v1` immediately after swapping `docs_live -> docs_v2` (destroys instant rollback if production latency or relevance degrades!).
- **RIGHT:** Keep `docs_v1` warm (read-only / shadow-synced) for `24–72h` post-cutover, then delete only after SLOs and zero-result rates stabilize.
- **WRONG:** Leaving `PIT` (Point-in-Time) handles unclosed with 1-hour keepalives on high-traffic pagination (pins deleted Lucene segments and exhausts heap/disk!).
- **RIGHT:** Use short PIT keepalives (`1m`) and explicitly `DELETE /_pit` once pagination finishes.

## 9. Testing & Verification
- Run `python -m unittest discover -s shadow-search/tests -v` (`test_search_relevance_acl_gate.py` verifies graded NDCG, MRR, Recall, duplicate hit accounting, and unauthorized/revoked ACL failure blocking!).

## 10. Operational Considerations
- Automate incremental reindexing via Transactional Outbox / CDC (`shadow-data` Module `05`) with a weekly count-parity check comparing `COUNT(active_oltp_docs)` vs `COUNT(indexed_docs)` per tenant.

## 11. Authoritative References
- OpenSearch / Elasticsearch Documentation — *Index Aliases & Point-in-Time (`PIT` + `search_after`)* (`https://www.elastic.co/guide/en/elasticsearch/reference/current/paginate-search-results.html`).
- Järvelin & Kekäläinen (ACM TOIS 2002) — *Cumulated Gain-Based Evaluation of IR Techniques (NDCG)*.

## 12. Limitations & When NOT to Use
- Offline relevance benchmarks (`Recall@K`/`NDCG@K`) capture labeled snapshot quality, NOT live click-through satisfaction or novel emerging slang; pair offline alias gates with online zero-result & click-rank telemetry (`/shadow-analytics`).
