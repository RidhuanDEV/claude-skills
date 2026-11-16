# Hybrid Retrieval (BM25 + Vector ANN + RRF), Analyzers & ACL Prefiltering

## 1. Hybrid Fusion Formula (Reciprocal Rank Fusion — Cormack et al., SIGIR 2009)
$$\text{RRF}(d) = \sum_{m \in M} \frac{1}{k + r_m(d)}, \quad k = 60 \text{ (standard smoothing constant)}$$
RRF fuses heterogeneous score scales (BM25 unbounded vs cosine $[-1, 1]$) safely without fragile min-max score normalization.

## 2. Retrieval Evaluation Metrics
- **`Recall@K`**: Fraction of relevant items retrieved in top $K$.
- **`MRR@K` (Mean Reciprocal Rank)**: $1 / \text{rank\_of\_first\_relevant\_doc}$.
- **`NDCG@K`**: Graded relevance discounted by $\log_2(i + 1)$, measuring ranking order quality.

## 3. Adversarial Cases & Controls
| Adversarial Case | Failure Mode | Required Control |
|---|---|---|
| **Permission-Revoked / Cross-Tenant Doc** | Tenant B sees Tenant A snippet or cached hit after permission revocation | Enforce pre-query `tenant_id` + ACL bitmask filter AND tombstone/delete from index + invalidate scoped cache |
| **Indonesian Slang / Typo / Morphology** | Unstemmed or over-strict cosine cutoff drops relevant results | Multi-field mapping (`keyword` exact + `indonesian` analyzer + trigram/fuzzy fallback) calibrated on held-out queries |
| **Deep Pagination Timeout** | `from + size > 10,000` blows up heap/CPU | Use `search_after` + Point-In-Time (`PIT`) cursor |
| **Zero-Downtime Mapping Change** | Dropping/rebuilding live index causes outage | Versioned index (`docs_v2`) + dual-write during backfill + atomic alias swap |
