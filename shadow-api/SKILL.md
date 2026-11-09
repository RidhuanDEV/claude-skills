---
name: shadow-api
description: "Test real HTTP API endpoints, generate OpenAPI 3.1 specifications from existing backends or new endpoints (compact or modular), and sync Postman v2.1 collections. Trigger with /shadow-api."
---

# /shadow-api — Real API Tester, OpenAPI 3.1 & Postman Sync (Shadow Army)

Use this skill whenever the **Monarch** invokes `/shadow-api`, asks to generate OpenAPI/Postman from an **existing backend**, or builds/updates backend API endpoints.
This skill connects directly to the **`shadow_api` MCP server** (`test_api_endpoint`, `upsert_openapi_endpoint`, `bulk_upsert_openapi_endpoints`, `validate_openapi_spec`, `sync_postman_collection`, `run_api_collection`).

## Workflow

1. **Generate OpenAPI + Postman from an Existing Backend (`bulk_upsert_openapi_endpoints`)**:
   - Scout the existing backend routes, controllers, validators (Zod/Joi/class-validator/Pydantic/Go structs), and response DTOs.
   - Call `bulk_upsert_openapi_endpoints` in a **single batch call** with `specPath: "<project>/docs/api/openapi.yaml"`, `autoSyncPostman: true`, and the full `endpoints` array.
   - Automatically selects **Compact Mode** (`docs/api/openapi.yaml`) for small projects (≤ 4 modules) or **Modular Mode** (`docs/api/modules/<module>.openapi.yaml` + bundled `docs/api/openapi.yaml` + nested Postman folders) for multi-module projects.
2. **Single Endpoint Upsert (`upsert_openapi_endpoint`)**:
   - When adding or modifying 1–2 endpoints during development, call `upsert_openapi_endpoint` followed by `sync_postman_collection`.
3. **Validate OpenAPI (`validate_openapi_spec`)**:
   - Ensure zero missing summaries or responses.
4. **Live HTTP Verification (`test_api_endpoint` / `run_api_collection`)**:
   - When the local/staging backend server is running, fire real HTTP requests to verify status codes, latency (`ms`), and response payloads, recording real responses directly into OpenAPI.
