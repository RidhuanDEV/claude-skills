# 03. Pre-Top-K Tenant ACL Filtering & Freshness Tombstones

## 1. Purpose & Activation Conditions
Enforce zero-leakage multi-tenant and document-level authorization **inside** search and vector engines BEFORE top-K scoring, facet counting, and caching — and guarantee near-real-time propagation of document deletions and permission revocations. Load whenever indexing multi-tenant/private corpora or auditing RAG retrieval security.

## 2. Prerequisites
- Canonical server principal + policy revision from `/shadow-auth` and `search_relevance_acl_gate.py`.

## 3. Technical Principles & Constraints
- **Mandatory Pre-Top-K ACL Filtering (NEVER Post-Filter!):**
  - **Why Post-Filtering Fails Catastrophically:** Fetching global `topK = 20` vectors across all tenants and running `.filter(doc => doc.tenantId === callerTenant)` in Node/Python: (1) returns **0 results** for small tenants crowded out by giant tenants' documents, (2) leaks document counts/facets across tenants, and (3) creates a single bug away from total cross-tenant data breach (`OWASP LLM09:2026`)!
  - **Mandatory Rule:** Pass `tenant_id` AND authorized `acl_principals` (`['user:u1', 'role:finance', 'group:g9']`) + `deleted = false` as an **indexed pre-filter** inside PostgreSQL `WHERE`, OpenSearch `bool.filter`, or Qdrant payload filter BEFORE scoring, facet aggregation, and top-K cutoffs!
- **Near-Real-Time Deletion & Revocation Tombstones:** When a user revokes a collaborator's access, deletes a document, or submits a UU PDP DSAR erasure (`/shadow-privacy`), stale search indexes can continue serving revoked content for hours if indexed only by nightly cron!
  - Emit a high-priority outbox tombstone event (`search.doc.revoked` / `search.doc.deleted`) processed within seconds (`<= 5–30s` SLA),
  - For strict zero-window revocation (e.g., legal/HR permissions), verify returned candidate `doc_id`s against an authoritative fast live ACL/tombstone revision check (Zookie / Redis revocation set) right before returning snippets to the user or LLM!
- **Serving-Code Verification Over Trace-Only Trust:** Passing `search_relevance_acl_gate.py` proves that a given exported trace contained 0 unauthorized docs — it does **NOT** prove by itself that the production retrieval engine actually applied the pre-filter before top-K! Always verify the actual query builder + index mapping + freshness pipeline in the serving codebase independently (`shadow-auth` Module `08`).

## 4. Architecture & Implementation
```sql
-- PostgreSQL Pre-Top-K Hybrid Retrieval (Strict Tenant + ACL Array + Active Tombstone Filter)
WITH lexical AS (
  SELECT id, ROW_NUMBER() OVER (ORDER BY ts_rank_cd(search_tsv, websearch_to_tsquery('indonesian', $4)) DESC) AS r_lex
  FROM doc_chunks
  WHERE tenant_id = $1
    AND deleted_at IS NULL
    AND acl_principals && $2::text[] -- Pre-filtered BEFORE top-K! (GIN indexed)
    AND search_tsv @@ websearch_to_tsquery('indonesian', $4)
  LIMIT 40
),
semantic AS (
  SELECT id, ROW_NUMBER() OVER (ORDER BY embedding <=> $3::vector ASC) AS r_vec
  FROM doc_chunks
  WHERE tenant_id = $1
    AND deleted_at IS NULL
    AND acl_principals && $2::text[] -- Identical strict pre-filter!
  LIMIT 40
)
SELECT
  COALESCE(l.id, s.id) AS doc_id,
  COALESCE(1.0 / (60 + l.r_lex), 0) + COALESCE(1.0 / (60 + s.r_vec), 0) AS rrf_score
FROM lexical l
FULL OUTER JOIN semantic s ON l.id = s.id
ORDER BY rrf_score DESC
LIMIT 10;
```
OpenSearch / Elasticsearch pre-filtered kNN + BM25 query clause:
```json
{
  "query": {
    "bool": {
      "filter": [
        { "term": { "tenant_id": "tenant-alpha" } },
        { "terms": { "acl_principals": ["user:alice", "group:finance"] } },
        { "term": { "deleted": false } }
      ],
      "must": [{ "multi_match": { "query": "aturan cuti tahunan", "fields": ["title^3", "body"] } }]
    }
  }
}
```

## 5. Platform / Vendor Variations
| Search Engine | Pre-Filter Mechanism | High-Churn ACL Caveat |
| :--- | :--- | :--- |
| **PostgreSQL + `pgvector`** | `WHERE tenant_id = $1 AND acl_principals && $2` (GIN on `acl_principals`) + RLS | Pair with `hnsw.iterative_scan = relaxed_order` on `pgvector >= 0.8` |
| **OpenSearch / Elasticsearch** | `bool.filter` + `knn.filter` (both mandatory!) | If a folder permission affects 100,000 docs, avoid reindexing 100k docs on every role edit — store `folder_id` / `group_id` tokens in index and expand user's permitted groups at query time! |
| **Qdrant** | Payload index on `tenant_id` (`is_tenant: true` optimizes disk locality per tenant!) | Must explicitly create keyword payload index before filtering |

## 6. Decision Matrix & Trade-Offs (Dynamic Permissions Scaling)
| ACL Granularity | Indexing Strategy | Revocation Latency |
| :--- | :--- | :---: |
| **Tenant-Wide Docs Only** | `tenant_id` keyword filter | Instant |
| **Role / Group Permissions** | Store `acl_groups[]` on doc; pass caller's live `groups[]` from `/shadow-auth` at query time | **Instant (zero reindex on user role change!)** |
| **Per-Document Direct Sharing (`ReBAC`)** | Index `acl_principals[]` via outbox + live Zookie/revocation verification | Seconds (`<= 5s`) + instant via live post-check |

## 7. Real Production Scenario
An HR employee leaves the `payroll-admins` group at 10:00 AM, yet at 2:00 PM their internal AI search assistant still retrieves confidential payroll spreadsheets because the search index only refreshed nightly and cached query embeddings globally. Switching to query-time live group expansion (`acl_principals && callerLiveGroups`), an outbox revocation tombstone synced in `< 5s`, and removing cross-user cache sharing eliminates stale ACL leaks completely.

## 8. Failure Modes & Edge Cases
- **WRONG:** Passing `tenant_id` only to the BM25 query while forgetting `knn.filter` on the parallel vector search branch (vector branch leaks Tenant B's chunks straight into RRF!).
- **RIGHT:** Apply the EXACT same `(tenant_id, acl_principals, deleted=false)` filter to **BOTH** lexical and vector branches + enforce `fuseHybridRankingsRrf` defense-in-depth tenant assertion!
- **WRONG:** Storing unencrypted search snippets of erased UU PDP subjects in index replicas after DSAR deletion.
- **RIGHT:** Delete search documents synchronously/via outbox during DSAR erasure and confirm receipt (`shadow-privacy` Module `03`).

## 9. Testing & Verification
- Run `python shadow-search/scripts/search_relevance_acl_gate.py --self-test` and `python -m unittest discover -s shadow-search/tests -v` (blocks ANY unauthorized or revoked document anywhere in the returned list, withholding metrics on ACL failure!).
- Write an integration test revoking a document -> immediately running search -> asserting `0` revoked hits returned.

## 10. Operational Considerations
- Monitor `search_index_freshness_lag_sec` (time from OLTP `updated_at`/`revoked_at` to search index visibility) as a Tier-1 SRE SLO (`< 30s` p99).

## 11. Authoritative References
- OWASP Top 10 for LLM Applications 2026 — `LLM09:2026` (*Vector and Embedding Weaknesses*) (`https://raw.githubusercontent.com/GenAI-Security-Project/GenAI-LLM-Top10/main/README.md`).
- Qdrant Multitenancy & Payload Indexing Docs (`https://qdrant.tech/documentation/guides/multiple-partitions/`).

## 12. Limitations & When NOT to Use
- Never embed hundreds of thousands of individual `user_id`s into a single document's `acl_principals[]` array (explodes inverted index size); model via group/role IDs or external ReBAC (`OpenFGA`) token expansion!
