# 01. API Contract Lifecycle & OpenAPI Governance

## 1. Purpose & Activation Conditions
Discover authoritative API documentation ownership, choose Code-First vs Contract-First workflows cleanly, prevent OpenAPI/viewer/collection drift, and integrate `shadow_api` MCP tools without creating competing specs. Load before creating, modifying, or documenting any backend endpoint.

## 2. Prerequisites
- Read-only `shadow_api` MCP (`discover_api_artifacts`, `compare_openapi_drift`, `validate_openapi_spec`) or direct repository inspection when MCP is unavailable.

## 3. Technical Principles & Constraints
- **Mandatory Step 0 — Ownership Discovery Before Editing:** Always trace routes -> generator config (`SwaggerModule`, FastAPI OpenAPI, `oapi-codegen`, `TypeSpec`) -> viewer (`Swagger UI`, `Scalar`, `Redoc`) -> client collections (`Postman`, `Bruno`, `Insomnia`) BEFORE editing any spec or route. Check `sourceOfTruth.verified`, `conflicts`, and `unresolvedReferences`.
- **Single Source of Truth Rule (Zero Competing Specs):**
  - **Code-First:** Update route decorators, DTOs, and validation schemas in code, then regenerate the spec via the project's established script. NEVER hand-edit generated output files!
  - **Contract-First:** Update the authoritative OpenAPI 3.1 / TypeSpec / GraphQL / Protobuf declaration first, validate with native linters (`spectral`, `redocly`, `buf`), and regenerate server stubs/SDKs.
- **Ambiguity Stop Gate (Generic Doc Requests):** If the repository has NO established API documentation workflow and the user makes an open request (e.g., `"Buatkan dokumentasi API"`), ask immediately via the interactive question tool with concrete options (Markdown reference vs checked-in OpenAPI 3.1 vs Postman/Bruno collection) and wait before creating persistent files.
- **Collection Preservation:** Preserve existing Bruno (`.bru`), Postman tests, auth configs, and environment variables. Never overwrite an existing collection blindly; create a new collection ONLY on explicit user intent.

## 4. Architecture & Implementation
```powershell
# Offline OpenAPI 3.x contract hygiene & breaking-diff verification (L0/L1)
python "shadow-api/scripts/api_contract_verifier.py" --self-test
python "shadow-api/scripts/api_contract_verifier.py" --check-openapi-contract path/to/openapi.json
python "shadow-api/scripts/api_contract_verifier.py" --check-breaking-diff path/to/v1.json path/to/v2.json
```
Authoritative OpenAPI 3.1 operation baseline (explicit `operationId`, typed errors, bounded params):
```yaml
openapi: 3.1.0
info:
  title: Orders Service API
  version: 1.2.0
paths:
  /api/v1/orders:
    post:
      operationId: createOrder
      x-requires-idempotency: true
      parameters:
        - name: Idempotency-Key
          in: header
          required: true
          schema:
            type: string
            format: uuid
      responses:
        "201":
          description: Order created
        "409":
          description: In-flight idempotency conflict
          content:
            application/problem+json:
              schema:
                $ref: "#/components/schemas/ProblemDetails"
```

## 5. Platform / Vendor Variations
| Stack | Typical Authoritative Source | Native Regeneration / Drift Check |
| :--- | :--- | :--- |
| **NestJS / FastAPI / Hono+Zod** | Code-First (decorators / Pydantic / Zod OpenAPI) | Export JSON in CI & diff against checked-in baseline (`compare_openapi_drift`) |
| **Go (`oapi-codegen`) / Enterprise Gateway** | Contract-First (`openapi.yaml` / `TypeSpec`) | `redocly lint` + codegen diff check in CI (`git diff --exit-code`) |
| **gRPC / ConnectRPC** | Contract-First (`.proto`) | `buf lint` + `buf breaking --against '.git#branch=main'` |

## 6. Decision Matrix & Trade-Offs
| Workflow | Refactoring Speed | Cross-Team Parallelism | Best Fit |
| :--- | :---: | :---: | :--- |
| **Code-First** | High (single edit in code) | Medium | Single-team full-stack apps (FastAPI, NestJS, Hono) |
| **Contract-First (OpenAPI 3.1 / TypeSpec)** | Medium | Very High (frontend/mobile generate mocks upfront) | Public partner APIs, multi-team platforms, regulated banking (SNAP BI) |

## 7. Real Production Scenario
A backend team uses NestJS `SwaggerModule` at `/docs-json` AND manually maintains a separate `docs/openapi.yaml` file. Over 6 months the two specs diverge on 14 endpoints, breaking mobile SDK generation. Running `discover_api_artifacts` reveals the dual-source conflict; consolidating on Code-First export into CI (`compare_openapi_drift`) and removing the stale duplicate spec restores 100% contract parity.

## 8. Failure Modes & Edge Cases
- **WRONG:** Editing a generated `swagger.json` by hand (overwritten on next build) or initializing a brand-new `postman_collection.json` when the team already maintains Bruno `.bru` files.
- **RIGHT:** Trace and update the single verified authoritative source, regenerate via established tooling, and synchronize collections in the team's existing format.
- **WRONG:** Omitting `operationId` or reusing duplicate `operationId`s across paths (breaks typed OpenAPI/SDK client generators).
- **RIGHT:** Enforce unique, stable `operationId`s (`listOrders`, `createOrder`) in CI via `api_contract_verifier.py`.

## 9. Testing & Verification
- Run `discover_api_artifacts`, `validate_openapi_spec`, and `compare_openapi_drift` (`shadow_api` MCP) plus `api_contract_verifier.py --check-openapi-contract` in CI.

## 10. Operational Considerations
- Keep generated SDKs/types (e.g., `openapi-typescript`) checked via CI drift gates so frontend consumers never silently fall out of sync with backend DTOs.

## 11. Authoritative References
- OpenAPI Specification v3.1.0 (`https://spec.openapis.org/oas/v3.1.0`).
- Redocly / Spectral OpenAPI Linting Rules (`https://redocly.com/docs/cli/`).

## 12. Limitations & When NOT to Use
- Do NOT force a heavy Contract-First OpenAPI/TypeSpec pipeline onto a tiny internal single-consumer monorepo where end-to-end typed `tRPC` or framework-native codegen already guarantees compile-time parity.
