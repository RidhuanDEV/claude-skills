---
name: shadow-api
description: "Backend API & Contract Engineering Specialist. Use when designing, modifying, or testing REST/GraphQL/gRPC/tRPC endpoints, discovering OpenAPI/viewer/collection ownership via shadow_api MCP, enforcing RFC 9457 errors, cursor pagination, Idempotency-Key retries, presigned uploads, outbound webhooks, or zero-breakage API versioning. Do NOT use for core domain modeling (/shadow-domain)."
---

# Shadow API (`/shadow-api`) — Backend API Design, Contract Governance & Real Testing

Use this skill whenever the **Monarch** creates, modifies, documents, versions, or tests backend API endpoints, synchronizes OpenAPI/Swagger specs and client collections via **`shadow_api` MCP**, or hardens pagination, idempotency, uploads, and multi-protocol transports.

## 1. Step 0 — Authoritative Ownership Discovery (`shadow_api` MCP First)

Pass the owning service's `projectRoot` and target protocol to read-only `discover_api_artifacts` BEFORE changing any endpoint, spec, or collection (or inspect the same repository evidence directly when MCP is unavailable). Check `coverage`, `conflicts`, `unresolvedReferences`, and `sourceOfTruth.verified`:
- **Code-First:** Update routes/DTOs/decorators in code and regenerate via the established workflow — **never manually edit generated output**.
- **Contract-First:** Update the authoritative OpenAPI 3.1 / TypeSpec / AsyncAPI / GraphQL / `.proto` contract and validate with native tooling — **never create competing duplicate specs**.
- **Viewers & Collections:** Trace Swagger UI / Scalar / Redoc to its source spec. Preserve existing Bruno/Postman/Insomnia tests, auth, and environments (`sync_postman_collection` initializes a new collection ONLY on explicit Postman intent and refuses overwrites).
- **Generic Doc Request Stop Gate:** If no maintained API doc workflow exists and the user asks generically (e.g., `"Buatkan dokumentasi API"`), ask immediately via the interactive question tool (Markdown reference vs checked-in OpenAPI 3.1 vs Postman/Bruno collection) and wait before creating persistent files.

## 2. Core API Engineering Workflow & Non-Negotiables

1. **Contract-First Hygiene & RFC 9457 Errors:** Enforce accurate RFC 9110 statuses + `application/problem+json` (`type`, `title`, `status`, `detail`, `instance`, `requestId`) with zero raw SQL/ORM/stack-trace leaks; serialize via explicit Response DTOs (anti-BOPLA).
2. **Idempotency & Bounded Pagination:** Require tenant-scoped `Idempotency-Key` (`payload_sha256` -> `422`, in-flight -> `409`, replay -> stored response) on retryable `POST` order/payment routes; enforce keyset/cursor pagination with unique tie-breakers and hard `limit <= 100`.
3. **Zero-Breakage Evolution & Verified Sync:** Check diffs with `compare_openapi_drift` / `api_contract_verifier.py --check-breaking-diff`, emit RFC 9745 `Deprecation: @<unix>` + RFC 8594 `Sunset` headers on deprecated routes, and verify official SDKs + structured JSON wide-event logging (`BACKEND.md §12`).
4. **Bounded Real Verification & Cleanup (`Rule #29`):** Exercise only affected routes on a verified local service via `test_api_endpoint` / bounded `run_api_collection`. If this task spawned a temporary local server solely for verification, stop that exact tracked PID (`resource_cleanup.py --cleanup-owned`) on exit without touching sibling workspace servers.

## 3. Deterministic Verification CLI & Scenario Benchmarks

Run offline checks (`L0`/`L1`) before claiming `VERIFIED-LOCAL`:
```powershell
python "shadow-api/scripts/api_contract_verifier.py" --self-test
python "shadow-api/scripts/api_contract_verifier.py" --check-problem-json path/to/error.json
python "shadow-api/scripts/api_contract_verifier.py" --check-openapi-contract path/to/openapi.json
python "shadow-api/scripts/api_contract_verifier.py" --check-breaking-diff path/to/v1.json path/to/v2.json
python -m unittest discover -s "shadow-api/tests" -v
```
Graded specialist scenarios live in [evaluations.md](evaluations.md) (10 scenarios covering idempotent timeout retry during v1->v2 migration, Code-First ownership, RFC 9457 hygiene, cursor pagination, presigned uploads, GraphQL depth/DataLoader, and outbound webhook SSRF).

## Reference Guide

Load **only** the 1–2 modules matching the active subtask (never load all 8 at once):

| Task / Scenario | Tier | Load Reference |
| :--- | :--- | :--- |
| Code-First vs Contract-First ownership, `shadow_api` MCP discovery, OpenAPI 3.1 & collections | CORE | [references/01-api-contract-lifecycle-and-openapi.md](references/01-api-contract-lifecycle-and-openapi.md) |
| RFC 9110 HTTP status semantics, RFC 9457 `application/problem+json` & zero stack/SQL leaks | CORE | [references/02-rest-http-semantics-and-rfc9457-errors.md](references/02-rest-http-semantics-and-rfc9457-errors.md) |
| Keyset/cursor pagination with tie-breakers, `limit <= 100` bounds & allowlisted sort/filters | CORE | [references/03-pagination-filtering-and-sorting.md](references/03-pagination-filtering-and-sorting.md) |
| Tenant-scoped `Idempotency-Key` (`409`/`422`/replay), transactional ledger & `If-Match` CAS | CORE | [references/04-idempotent-mutations-and-concurrency.md](references/04-idempotent-mutations-and-concurrency.md) |
| GraphQL (per-request DataLoader, depth/cost limits), gRPC/Protobuf (`reserved`), ConnectRPC & tRPC | ADVANCED | [references/05-multi-protocol-graphql-grpc-trpc.md](references/05-multi-protocol-graphql-grpc-trpc.md) |
| Presigned S3/R2 uploads, magic-byte validation, `202 Accepted` LRO & SSRF-safe signed webhooks | ADVANCED | [references/06-uploads-presigned-urls-and-lro.md](references/06-uploads-presigned-urls-and-lro.md) |
| Tiered rate limits (`RateLimit-*`), explicit Response DTOs, wide-event logging & server cleanup | OPERATIONAL | [references/07-rate-limits-auth-boundaries-and-observability.md](references/07-rate-limits-auth-boundaries-and-observability.md) |
| Additive evolution, RFC 9745 `Deprecation` / RFC 8594 `Sunset`, `v1 -> v2` coexistence & Pact/diff CI | OPERATIONAL | [references/08-versioning-deprecation-and-contract-testing.md](references/08-versioning-deprecation-and-contract-testing.md) |

Do not load unrelated references unnecessarily.
