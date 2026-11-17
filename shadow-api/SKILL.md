---
name: shadow-api
description: "Backend API & Contract Sync. Use when creating, modifying, or testing HTTP/REST API endpoints, discovering or updating OpenAPI/Swagger specs (any folder, filename, or layout), or keeping the project's existing API client collection (Bruno, Postman, Insomnia, Hoppscotch, Thunder Client, .http) in sync via shadow_api MCP."
---

# /shadow-api — Real API Tester, OpenAPI Discovery & Existing-Collection Sync (Shadow Army)

Use this skill whenever the **Monarch** invokes `/shadow-api`, asks to generate or update OpenAPI/Swagger specs from an **existing backend**, or builds/updates backend API endpoints.
This skill connects directly to the **`shadow_api` MCP server** (`discover_api_artifacts`, `test_api_endpoint`, `upsert_openapi_endpoint`, `bulk_upsert_openapi_endpoints`, `validate_openapi_spec`, `sync_postman_collection`, `run_api_collection`).

## Step 0 — Discover Existing OpenAPI Specs & API Client Collections First (Never Impose Layouts or Postman)

Before creating or updating any OpenAPI file or collection, call **`discover_api_artifacts`** (read-only) with `projectRoot` (or inspect the repo). Never hardcode `docs/api/openapi.yaml` or generate Postman blindly:
- **Existing OpenAPI / Swagger specs** (any directory such as `.`, `docs/`, `docs/api/`, `swagger/`, `api/`, `spec/`, `contracts/`, any `.yaml`/`.yml`/`.json` filename, OpenAPI `3.x` or Swagger `2.0`, single-file or modular `modules/`/`paths/`/`domains/`/`endpoints/`/`specs/`):
  - **Single existing spec found:** Update that exact file in place (the MCP auto-resolves even if `specPath` points to default `docs/api/openapi.yaml` via `resolvedFromExisting: true`). Preserve brownfield single-file specs (`allowAutoSplit: false` by default) and existing modular layouts/filenames (`<slug>.yaml` vs `<slug>.openapi.yaml`, `$ref` routes, and `components`).
  - **Multiple OpenAPI specs found:** Ask the Monarch or pass the exact `specPath` for the target service (`allowNewSpec: true` only when intentionally creating a new spec).
  - **None found:** Create `docs/api/openapi.yaml` (or the path requested by the Monarch).
- **Existing API client collections** (anywhere in the project tree):
  - **Bruno (`bruno.json` / `*.bru`):** Keep Bruno as the source of truth. Create/update `.bru` requests matching the project's existing folder layout, naming, `environments/*.bru`, and `assert`/`tests` style (`reference/sub-QA-AUTOMATION.md`). Do NOT create `postman_collection.json` / `postman_environment.json`.
  - **Postman (`*postman_collection*.json`):** Update the existing detected Postman collection path via `sync_postman_collection`.
  - **Insomnia / Hoppscotch / Thunder Client / `.http` / `.rest`:** Update that existing format directly; do NOT create Postman files alongside it.
  - **Nothing detected:** Produce OpenAPI only and ask the Monarch which client format they want; generate Postman only when explicitly requested (`collectionFormat: "postman"` or `force: true`).

## Workflow

1. **Discover & Generate/Update OpenAPI (`discover_api_artifacts` -> `bulk_upsert_openapi_endpoints`)**:
   - Run `discover_api_artifacts` first, then scout backend routes, controllers, validators (Zod/Joi/class-validator/Pydantic/Go structs), and response DTOs.
   - Call `bulk_upsert_openapi_endpoints` in a **single batch call** passing `specPath` (discovered spec path, or `"<project>/docs/api/openapi.yaml"` on greenfield), `collectionFormat: "auto"`, and the full `endpoints` array; read `detectedCollectionFormat` / `collectionNote` in the result and act on it.
   - Greenfield projects default to **Compact Mode** (≤ 4 modules) or **Modular Mode** (> 4 modules). Existing brownfield single-file specs stay single-file unless `allowAutoSplit: true` is passed.
2. **Single Endpoint Upsert (`upsert_openapi_endpoint`)**:
   - When adding or modifying 1–2 endpoints during development, pass the discovered `specPath` (or let the MCP auto-resolve a unique existing spec), then update the **existing** client collection format (`.bru`, `.http`, etc., or `sync_postman_collection` only for Postman projects).
3. **Validate OpenAPI (`validate_openapi_spec`)**:
   - Ensure zero missing summaries or responses.
4. **Live HTTP Verification (`test_api_endpoint` / `run_api_collection`)**:
   - When the local/staging backend server is running, fire real HTTP requests to verify status codes, latency (`ms`), and response payloads, recording real responses directly into OpenAPI.
5. **Contract-First, RFC 9457 Errors, Idempotency & Pagination Discipline**:
   - **Standard Error Envelope**: Use structured `application/problem+json` (RFC 9457: `type`, `title`, `status`, `detail`, `instance` / `errors[]`) without leaking stack traces or internal SQL errors.
   - **Idempotency & Pagination**: Enforce `Idempotency-Key` semantics on non-idempotent payment/order `POST` routes (`/shadow-concurrency`/`/shadow-cache`); enforce bounded cursor (`seek` / keyset) or validated offset pagination (`limit <= 100`) with stable sort keys (tie-broken by `id`).
   - **Evolution & Negative Testing**: Document breaking vs additive changes (`/shadow-compat`), emit `Deprecation`/`Sunset` headers before removing fields, and test invalid payloads (`400/422`), unauthorized (`401/403`), and conflicts (`409`).
6. **Official-First SDK & Verified Auth Claims (`OFFICIAL-FIRST-DEPENDENCY-POLICY.md`):** Reuse existing trusted SDKs and official framework packages before custom wrappers, verify packages non-destructively before install, never invent unsupported SDK methods/endpoints, and never trust frontend-supplied `username` without server-verified auth claims.
