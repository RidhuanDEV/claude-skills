# Search Relevance Benchmark & Alias Migration Playbook

## Zero-Downtime Reindex Runbook
1. Create `index_v2` with updated analyzers/dimensions (`kNN` HNSW params).
2. Enable dual-write (or CDC outbox sync) so new mutations hit both `v1` and `v2`.
3. Reindex historical snapshot with throttled batching + verify document count & tombstone parity.
4. Run held-out `search_relevance_acl_gate.py --evaluate` confirming `NDCG@K` >= baseline and `0` ACL leaks.
5. Atomic alias swap `index_live: v1 -> v2`; retain `v1` for 24–72h instant rollback before deletion.
