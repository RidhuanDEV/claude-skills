# Full-Stack Search Architecture: Engines, Query Understanding & Ingestion

## 1. Core Concepts
Production search combines **right-sized engine selection**, **mandatory pre-top-K tenant/ACL filtering**, **hybrid lexical + vector Reciprocal Rank Fusion (RRF)**, **Indonesian/multilingual query normalization**, and **zero-downtime alias reindexing**.

## 2. Technical Rules & Engine Selection Matrix

| Corpus & Query Profile | Choose Engine | Why / Operational Boundary |
| :--- | :--- | :--- |
| `< 1M` docs, already on PostgreSQL, keyword + fuzzy + vector | **PostgreSQL (`tsvector`/GIN + `pg_trgm` + `pgvector` HNSW)** | Zero extra cluster ops; atomic consistency with primary tables. |
| Instant typo-tolerant autocomplete (`< 20M` docs), low ops | **Meilisearch** or **Typesense** | Out-of-the-box prefix/typo ranking and scoped tenant search tokens. |
| Complex enterprise search, custom analyzers, facets (`> 10M` docs) | **OpenSearch** or **Elasticsearch** | Alias-based zero-downtime reindex, `PIT` + `search_after` deep pagination. |
| High-scale dense/sparse vector ANN (`> 10M` chunks) | **Qdrant** or **Milvus** | Payload pre-filtering (`tenant_id`, `acl_groups`) executed during HNSW traversal. |

## 3. Implementation Examples
```ts
// 1. Reciprocal Rank Fusion (RRF) with Mandatory Tenant Pre-Filter Verification
export interface RankedCandidate {
  readonly docId: string
  readonly tenantId: string
  readonly erased: boolean
}

export function fuseHybridRankingsRrf(
  callerTenantId: string,
  bm25List: ReadonlyArray<RankedCandidate>,
  vectorList: ReadonlyArray<RankedCandidate>,
  k = 60,
  topK = 20,
): ReadonlyArray<{ readonly docId: string; readonly rrfScore: number }> {
  const scores = new Map<string, number>()
  const accumulate = (list: ReadonlyArray<RankedCandidate>): void => {
    let validRank = 1
    for (const item of list) {
      // Defense-in-depth: reject any cross-tenant or erased document leaked by an upstream retriever
      if (item.tenantId !== callerTenantId || item.erased) {
        throw new Error(`SECURITY_ACL_VIOLATION: unauthorized document ${item.docId} entered ranking pool`)
      }
      scores.set(item.docId, (scores.get(item.docId) ?? 0) + 1 / (k + validRank))
      validRank += 1
    }
  }
  accumulate(bm25List)
  accumulate(vectorList)
  return [...scores.entries()]
    .map(([docId, rrfScore]) => ({ docId, rrfScore }))
    .sort((a, b) => b.rrfScore - a.rrfScore)
    .slice(0, topK)
}
```

## 4. Best Practices
- Index both a **stemmed/analyzed field** (for recall on Indonesian affixes `pengajuan -> aju`) and an **exact keyword/unstemmed sub-field** boosted `2x–3x` (so exact SKUs, regulation numbers `Perpres 46/2025`, and acronyms rank #1).
- Enable fuzzy typo matching (`AUTO`) only for tokens `>= 4` characters so short codes (`NIK`, `ID`, `VA`) do not false-match noisy neighbors.

## 5. Anti-patterns (WRONG vs RIGHT)
- **WRONG:** Fetching top-20 vector ANN results globally across all tenants and filtering by `tenantId` in application memory afterward (causes empty results for small tenants and cross-tenant timing/facet leaks).
- **RIGHT:** Apply `WHERE tenant_id = :tenantId AND erased = false` as an index **pre-filter** inside the database/vector engine before top-K and before facet aggregation.
- **WRONG:** Updating analyzer mappings in-place on a live index (corrupts tokenization consistency).
- **RIGHT:** Build a new versioned index (`docs_v2`), verify `Recall@K`/`NDCG@K` and 0 ACL leaks, then atomically swap the read alias (`docs_current -> docs_v2`).

## 6. Production Considerations
- Measure retrieval quality (`Recall@K`, `MRR@K`, `NDCG@K`) separately from downstream LLM generation faithfulness (`/shadow-eval`), stratified by language and query cohort.
