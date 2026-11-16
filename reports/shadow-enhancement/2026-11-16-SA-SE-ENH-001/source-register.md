# Phase 0 — Upstream Technical Source Register (`SA-SE-ENH-001`)

| Source ID | Title | Canonical URL | Publisher | Relevant Scope / Version | Retrieved At | Licensing / Access | Usage Scope | Status |
|---|---|---|---|---|---|---|---|---|
| `SRC-01` | RFC 9457 — Problem Details for HTTP APIs | `https://www.rfc-editor.org/rfc/rfc9457` | IETF | Current (obsoletes RFC 7807) | `2026-11-16` | Public standard | `/shadow-api` error envelope | Primary |
| `SRC-02` | RFC 9110 — HTTP Semantics (Idempotent Methods) | `https://www.rfc-editor.org/rfc/rfc9110` | IETF | Current HTTP/1.1–3 semantics | `2026-11-16` | Public standard | `/shadow-api`, `/shadow-concurrency` | Primary |
| `SRC-03` | PostgreSQL Transaction Isolation & MVCC | `https://www.postgresql.org/docs/current/transaction-iso.html` | PostgreSQL Global Dev Group | PostgreSQL 15–18 docs | `2026-11-16` | Public official docs | `/shadow-data`, `/shadow-db`, `/shadow-concurrency` | Primary |
| `SRC-04` | W3C Trace Context Specification | `https://www.w3.org/TR/trace-context/` | W3C | W3C Recommendation (`traceparent`) | `2026-11-16` | Public standard | `/shadow-observe`, `/shadow-debug` | Primary |
| `SRC-05` | WHATWG HTML Server-Sent Events (`EventSource` / `Last-Event-ID`) & RFC 6455 WebSocket | `https://html.spec.whatwg.org/multipage/server-sent-events.html` | WHATWG / IETF | Living Standard / RFC 6455 | `2026-11-16` | Public standard | `/shadow-realtime` | Primary |
| `SRC-06` | OWASP ASVS 5.0.0 & NIST SSDF SP 800-218 | `https://csrc.nist.gov/pubs/sp/800/218/final` | NIST / OWASP | ASVS 5.0.0 / SP 800-218 | `2026-11-16` | Public normative | `/shadow-sec`, `/shadow-auth`, `/shadow-supplychain` | Primary |
| `SRC-07` | CycloneDX (ECMA-424) / SPDX & SLSA v1.0 Provenance | `https://slsa.dev/spec/v1.0/` | OpenSSF / ECMA / Linux Foundation | SLSA v1.0 / CycloneDX 1.6 / SPDX 2.3+ | `2026-11-16` | Public specification | `/shadow-supplychain`, `/shadow-release` | Primary |
| `SRC-08` | Okapi BM25 & Reciprocal Rank Fusion (Cormack et al., SIGIR 2009) | `https://dl.acm.org/doi/10.1145/1571941.1572114` | ACM SIGIR | Peer-reviewed IR ranking fusion | `2026-11-16` | Academic reference (abstract/equation) | `/shadow-search` | Primary (Peer-Reviewed) |
| `SRC-09` | UU No. 27 Tahun 2022 (UU PDP), Perpres 46/2025, PADK OJK 1/2026 | `https://peraturan.bpk.go.id/` | Pemerintah RI / OJK | Verified 2026-11-16 | `2026-11-16` | Public statutory law | `/shadow-privacy`, `/shadow-presales`, `/shadow-grc` | Primary |
| `SRC-10` | Vendor / Runtime Specific Docs (Redis, OpenSearch, BullMQ, Kafka) | — | Respective Maintainers | Must match target repo lockfile version via `/context7` | `2026-11-16` | Version-bound | All specialists at execution time | `UNVERIFIED` until target repo lockfile inspected |
