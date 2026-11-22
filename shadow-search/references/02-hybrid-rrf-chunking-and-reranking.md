# 02. Hybrid RRF Fusion, Chunking & Reranking

## 1. Purpose & Activation Conditions
Combine lexical BM25 and dense vector ANN search cleanly using **Reciprocal Rank Fusion (RRF)**, structure-aware document chunking, and latency-bounded cross-encoder reranking — without falling for uncalibrated fixed cosine similarity thresholds. Load when designing hybrid search or improving RAG retrieval `Recall@K` and `NDCG@K`.

## 2. Prerequisites
- Lexical analyzer (`01`), pre-top-K tenant ACL enforcement (`03`), and graded relevance evaluation fixtures (`04`).

## 3. Technical Principles & Constraints
- **Structure-Aware Chunking > Blind Fixed-Character Slicing:** Never split legal contracts, Markdown docs, or tables mid-sentence or mid-table with blind `500`-char slices! Chunk along semantic boundaries (headings, paragraphs, clauses, complete table blocks — typically `300–700` tokens with `10%–15%` overlap) AND prepend **contextual document metadata** (`[Doc: UU PDP 27/2022 > Bab VII > Pasal 56]`) into every chunk so standalone embeddings preserve parent context!
- **Reciprocal Rank Fusion (RRF) Over Raw Score Linear Sums:** BM25 scores (`0..35+`, unbounded) and cosine similarities (`-1..1`) are on incompatible scales! RRF fuses ranked positions cleanly without fragile score normalization:
  $$\text{RRF}(d) = \sum_{r \in \{\text{BM25}, \text{Vector}\}} \frac{w_r}{k + \text{rank}_r(d)} \qquad (k = 60\text{ default})$$
- **No Uncalibrated Fixed Cosine Cutoffs (CRITICAL):** NEVER hardcode `WHERE cosine_similarity > 0.78` arbitrarily! Embedding models differ wildly in cosine distributions across languages (`en` vs `id` vs slang). Calibrate any score cutoff strictly against precision/recall curves on a held-out labeled dataset (including explicit abstention queries)!
- **Bounded Cross-Encoder Reranking:** Run neural rerankers (Cohere Rerank, BGE-Reranker, Jina) ONLY on the top `20–40` fused RRF candidates (NEVER top `200`!), with a tight timeout (`<= 400–600ms`) and automatic fallback to RRF order if the reranker times out!

## 4. Architecture & Implementation
```typescript
export interface RankedCandidate {
  readonly docId: string;
  readonly tenantId: string;
  readonly erased: boolean;
}

export interface FusedResult {
  readonly docId: string;
  readonly rrfScore: number;
}

export function fuseHybridRankingsRrf(
  callerTenantId: string,
  bm25List: readonly RankedCandidate[],
  vectorList: readonly RankedCandidate[],
  k = 60,
  topK = 20,
  bm25Weight = 1.0,
  vectorWeight = 1.0
): readonly FusedResult[] {
  const scores = new Map<string, number>();

  const accumulate = (list: readonly RankedCandidate[], weight: number): void => {
    const seenInList = new Set<string>();
    let rank = 1;
    for (const item of list) {
      // Defense-in-depth: fail loudly if any cross-tenant or erased doc leaked past upstream pre-filter!
      if (item.tenantId !== callerTenantId || item.erased) {
        throw new Error(`SECURITY_ACL_VIOLATION: unauthorized document '${item.docId}' entered RRF pool`);
      }
      if (!seenInList.has(item.docId)) {
        seenInList.add(item.docId);
        scores.set(item.docId, (scores.get(item.docId) ?? 0) + weight / (k + rank));
      }
      rank += 1;
    }
  };

  accumulate(bm25List, bm25Weight);
  accumulate(vectorList, vectorWeight);

  return [...scores.entries()]
    .map(([docId, rrfScore]) => ({ docId, rrfScore }))
    .sort((a, b) => b.rrfScore - a.rrfScore)
    .slice(0, topK);
}
```
PostgreSQL `pgvector` HNSW index with explicit pre-filter awareness (`pgvector 0.8+ iterative_scan`):
```sql
-- HNSW cosine index; enable hnsw.iterative_scan = relaxed_order on pgvector >= 0.8 for selective tenant filters!
CREATE INDEX CONCURRENTLY idx_doc_chunks_embedding_hnsw
  ON doc_chunks USING hnsw (embedding vector_cosine_ops)
  WITH (m = 16, ef_construction = 128);
```

## 5. Platform / Vendor Variations
| Vector Engine | Pre-Filtered ANN Behavior | Tuning Lever |
| :--- | :--- | :--- |
| **`pgvector` (`>= 0.8`)** | Supports `SET LOCAL hnsw.iterative_scan = relaxed_order;` so small-tenant `WHERE tenant_id = $1` filters don't under-fill top-K! | `hnsw.ef_search` (`40–100`), partial/partitioned indexes per giant tenant |
| **Qdrant** | Native payload index (`tenant_id` keyword) integrated inside HNSW graph traversal | Create payload index on `tenant_id` & `acl_groups` BEFORE querying! |
| **OpenSearch / Elasticsearch** | Native hybrid search pipeline (`normalization-processor` / RRF) + `knn.filter` pre-filter | Always pass `tenant_id` inside `knn.filter`, never post-query! |

## 6. Decision Matrix & Trade-Offs
| Retrieval Pipeline | Latency (p95) | Quality (`NDCG@10`) | Compute Cost |
| :--- | :---: | :---: | :---: |
| **BM25 Only** | `< 20ms` | Medium (misses paraphrases) | Lowest |
| **Dense Vector Only** | `20–50ms` | Medium (misses exact IDs/clauses) | Low–Medium |
| **Parallel BM25 + Vector RRF (`k=60`)** | `30–60ms` | **High** | Low–Medium (**Default**) |
| **Hybrid RRF + Cross-Encoder Rerank (Top 25 -> Top 8)** | `150–450ms` | **Highest (+8%–18% NDCG)** | Medium |

## 7. Real Production Scenario
An enterprise search team adds `WHERE (1 - (embedding <=> $1)) > 0.80` to "reduce hallucinations". Suddenly 62% of valid Bahasa Indonesia queries return **0 results** because the multilingual embedding model scores Indonesian-to-Indonesian matches between `0.62` and `0.74`! Removing the arbitrary `0.80` cutoff, switching to parallel BM25 + `pgvector` HNSW fused via `fuseHybridRankingsRrf` + top-20 cross-encoder reranking lifts `Recall@10` on Bahasa Indonesia queries from `0.38` to `0.91` (`search_relevance_acl_gate.py`).

## 8. Failure Modes & Edge Cases
- **WRONG:** Deduplicating chunks by rank AFTER computing RRF without tracking `seenInList` (a duplicated chunk inside one retriever gets double-counted!).
- **RIGHT:** Track `seenInList` per retriever and verify `duplicate_hits_at_k === 0` in `search_relevance_acl_gate.py`.
- **WRONG:** Changing the embedding model (`text-embedding-3-small -> bge-m3`) for new documents while keeping old vectors in the same index (vectors from different models live in completely incompatible vector spaces!).
- **RIGHT:** Re-embed the entire corpus into a fresh versioned index (`docs_v2`) and perform an atomic alias swap (`04`).

## 9. Testing & Verification
- Compare `BM25-only` vs `Vector-only` vs `Hybrid RRF` vs `RRF + Rerank` on the exact same frozen graded fixture using `python shadow-search/scripts/search_relevance_acl_gate.py --evaluate <eval.json>`.

## 10. Operational Considerations
- Monitor `rerank_timeout_fallback_rate` and `embedding_cache_hit_rate` so an overloaded reranker gracefully falls back to RRF without stalling RAG TTFT.

## 11. Authoritative References
- Cormack, Clarke & Buettcher (SIGIR 2009) — *Reciprocal Rank Fusion Outperforms Condorcet and Individual Rank Learning Methods*.
- `pgvector` Official Docs — *HNSW & Iterative Index Scans* (`https://github.com/pgvector/pgvector`).

## 12. Limitations & When NOT to Use
- Cross-encoder rerankers add `100–400ms` latency — skip reranking on instant keystroke autocomplete (`< 50ms` budget) and reserve it for Q&A, RAG, and complex document search.
