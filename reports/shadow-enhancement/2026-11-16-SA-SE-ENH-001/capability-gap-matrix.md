# Phase 0 — Capability Gap Matrix (`SA-SE-ENH-001`)

Status classification: `EXISTS` | `PARTIAL` | `MISSING` | `UNVERIFIED`

## 1. Candidate New Specialist Skills (`§3`)
| Candidate Skill | Priority | Status | Gap Summary |
|---|---|---|---|
| `/shadow-debug` | P0 | `PARTIAL` | Only `reference/DEBUGGING.md` (`81` lines) & post-prod SLA `shadow-maintain` exist; lacks hypothesis falsification gate, bisect/minimal repro protocol, async/race/memory diagnostics, and mandatory red-before/green-after regression proof script |
| `/shadow-concurrency` | P0 | `PARTIAL` | Outbox/idempotency rules are fragmented across `shadow-integrate`, `shadow-data`, and `shadow-cache`; lacks unified state-machine & crash-between-commit-and-ack invariant engine, poison DLQ, and explicit no-false-exactly-once verifier |
| `/shadow-refactor` | P0 | `PARTIAL` | Only `reference/REFACTORING.md` (`67` lines) + M&A `shadow-modernize` exist; lacks code-level characterization test gate, precedent matching enforcement, branch-by-abstraction playbook, and untouched-file diff verifier |
| `/shadow-domain` | P1 | `MISSING` | `shadow-discovery` handles PRD/SRS and `shadow-architect` handles topology; no dedicated DDD bounded context, aggregate invariant, domain event vs CRUD boundary modeling skill or transition verifier |
| `/shadow-search` | P1 | `PARTIAL` | `sub-RAG-VECTOR-KNOWLEDGE.md` covers RAG chunking/RRF prose, and `shadow-eval` checks LLM outputs; lacks standalone search subsystem skill (BM25/Indonesian morphology, alias zero-downtime reindex, `NDCG@K`/`MRR@K` + tenant ACL verifier) |
| `/shadow-realtime` | P1 | `PARTIAL` | Only `sub-REALTIME-IOT-DESKTOP.md` (`53` lines) exists; lacks protocol ADR (`WS`/`SSE`/`Polling`), mid-connection token revocation gate, `Last-Event-ID` cursor resume, slow-consumer backpressure & fan-out verification |
| `/shadow-supplychain` | P1 | `PARTIAL` | `shadow-sec` mentions SBOM/audit in 4 lines; lacks CycloneDX/SPDX vs lockfile graph reconciler, typosquatting/dependency confusion detector, pinned SHA CI/container policy, SLSA provenance, and waiver expiry verifier |

## 2. Existing Skills Deepening Gaps (`§4`)
| Skill | Status | Specific Gap Found in Inspection |
|---|---|---|
| `shadow-monarch` | `PARTIAL` | Has `CODEBASE-INTELLIGENCE.md` & `skill_router.py` (flat `companion_skills[]`), but lacks formal §2.2 Router Decision Record (`primary_skill`, `supporting_skills`, `risk_review_skills`, `excluded_skills`, permissions), §4.1 6-step Repo-Native Protocol block, and §7.2 unified result schema |
| `shadow-quality` | `PARTIAL` | Has `shadow_gate.py` & `codebase_intelligence.py`; `SKILL.md` lacks architectural fitness rules, forbidden cross-layer dependency checks, and change-risk scoring |
| `shadow-test` | `PARTIAL` | Strong polyglot matrix (`POLYGLOT-TESTING-MATRIX.md`), missing property-based tests, mutation testing guidance, state-machine transition testing, and flaky-test triage protocol |
| `shadow-architect` | `PARTIAL` | Has C4/ADR/Modular Monolith; missing explicit consistency models, distributed failure assumptions (split-brain/clock skew), and architectural fitness functions |
| `shadow-auth` | `PARTIAL` | Missing object/tenant policy test matrix, session revocation propagation, and confused deputy / privilege escalation test gate |
| `shadow-data` | `PARTIAL` | Missing explicit transaction isolation anomaly catalog (read/write skew, phantom), lock/deadlock timeouts, CDC & outbox transaction boundary |
| `shadow-db` | `PARTIAL` | Missing query planner cardinality/selectivity rules, MVCC bloat/vacuum, lock wait diagnostics, and safe `EXPLAIN` protocol |
| `shadow-api` | `PARTIAL` | `SKILL.md` (`22` lines) delegates to `shadow_api` MCP; lacks RFC 9457 Problem Details envelope, idempotency semantics, cursor vs offset pagination consistency, and deprecation sunset policy |
| `shadow-cache` | `PARTIAL` | Missing explicit cache coherency boundaries, TTL jitter, multi-tier invalidation, and tenant/user-scoped authorization-safe cache keys |
| `shadow-integrate` | `PARTIAL` | Missing explicit webhook timestamp/nonce replay window, reconciliation loop, partial failure recovery, and outbox handoff to `/shadow-concurrency` |
| `shadow-sec` | `PARTIAL` | Missing exploitability reachability context, multi-hop authz attack paths, attack-surface diff review, and handoff to `/shadow-supplychain` |
| `shadow-perf` | `PARTIAL` | Strong `k6` OpenAPI scaffold (`54` lines), missing profiling-before-optimization rule, CPU/heap/I/O triage, and run-to-run variance longitudinal baseline |
| `shadow-ops` | `PARTIAL` | Missing IaC drift checks, progressive delivery (canary/blue-green), zero-downtime secret rotation, and dry-run rollback verification |
| `shadow-observe` | `PARTIAL` | Missing W3C `traceparent` async propagation, high-cardinality label guardrails, PII redaction in traces, and handoff to `/shadow-debug` |
| `shadow-resilience` | `PARTIAL` | Missing scoped fault-injection harness, dependency outage degradation matrix, queue recovery, and bulkhead isolation |
| `shadow-maintain` | `PARTIAL` | Missing explicit diagnostic handoff boundary to `/shadow-debug` and postmortem countermeasure tracking |
| `shadow-eval` | `PARTIAL` | Needs explicit retrieval-ranking handoff with `/shadow-search`, dataset versioning, held-out split enforcement, and judge calibration |
| `shadow-compat` | `PARTIAL` | Needs explicit schema evolution matrix (backward/forward/full), consumer-driven contract checks, and semantic API diffing |
| `shadow-git` | `PARTIAL` | Needs explicit multi-agent worktree ownership boundaries and conflict reconciliation rules preserving both sides' invariants |
| `shadow-release` | `PARTIAL` | Needs explicit `/shadow-supplychain` provenance/SBOM proof handoff, migration-before-code ordering, and missing-artifact release block |
