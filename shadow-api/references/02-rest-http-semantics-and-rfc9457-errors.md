# 02. REST HTTP Semantics & RFC 9457 Error Envelopes

## 1. Purpose & Activation Conditions
Enforce accurate HTTP semantics (RFC 9110) and machine-readable, zero-leakage error envelopes (**RFC 9457 `application/problem+json`**) across all REST endpoints. Load when designing API routes, status codes, validation error formats, or global exception filters.

## 2. Prerequisites
- Centralized exception-handling middleware and structured JSON logger with `requestId`/`traceId` propagation (`BACKEND.md §12`).

## 3. Technical Principles & Constraints
- **Accurate HTTP Method & Status Semantics (RFC 9110):**
  - `GET`/`HEAD` are safe & idempotent (never mutate state on `GET`!). `PUT`/`DELETE` are idempotent; `POST` is non-idempotent unless guarded by `Idempotency-Key` (`04`).
  - Use exact status codes: `200 OK`, `201 Created` (with `Location` header), `202 Accepted` (async LRO), `204 No Content`, `400 Bad Request` (malformed syntax), `401 Unauthorized` (missing/invalid auth), `403 Forbidden` (authenticated but denied), `404 Not Found` (missing or concealed cross-tenant resource), `409 Conflict` (state/uniqueness/lock conflict), `422 Unprocessable Content` (valid JSON failing domain/field validation), `429 Too Many Requests` (with `Retry-After`), `503 Service Unavailable`. NEVER return `200 OK` wrapping `{ "success": false, "error": "..." }`!
- **RFC 9457 `application/problem+json` Standard:** Every `4xx`/`5xx` API response sets `Content-Type: application/problem+json` and includes `type` (stable machine-readable error URI/code), `title` (short summary), `status` (integer matching HTTP code), `detail` (safe human message), `instance` (request path), `requestId` (correlation ID), and optional typed `errors[]` (`{ field, code, message }`) for `422` validation failures.
- **Zero Internal Leakage:** NEVER expose stack traces, raw SQL/PostgreSQL `SQLSTATE` messages, Prisma/ORM exception classes, internal hostnames, or secrets in HTTP error responses — log diagnostics privately with `requestId` and return a clean generic `detail` on `5xx`.

## 4. Architecture & Implementation
```typescript
export interface FieldViolation {
  readonly field: string;
  readonly code: string;
  readonly message: string;
}

export interface ProblemDetails {
  readonly type: string;
  readonly title: string;
  readonly status: number;
  readonly detail: string;
  readonly instance: string;
  readonly requestId: string;
  readonly errors?: readonly FieldViolation[];
}

export function buildProblemDetails(input: {
  readonly status: number;
  readonly slug: string;
  readonly title: string;
  readonly detail: string;
  readonly instance: string;
  readonly requestId: string;
  readonly errors?: readonly FieldViolation[];
}): ProblemDetails {
  const safeDetail =
    input.status >= 500
      ? 'An unexpected server error occurred. Reference the requestId when contacting support.'
      : input.detail;
  return {
    type: `https://api.example.com/problems/${input.slug}`,
    title: input.title,
    status: input.status,
    detail: safeDetail,
    instance: input.instance,
    requestId: input.requestId,
    ...(input.errors && input.errors.length > 0 ? { errors: input.errors } : {}),
  };
}
```

## 5. Platform / Vendor Variations
| Framework | Global RFC 9457 Integration | Pitfall to Watch |
| :--- | :--- | :--- |
| **Express / Hono / Fastify** | Centralized error middleware setting `Content-Type: application/problem+json` | Default Express error handler prints HTML stack traces if `NODE_ENV !== 'production'` |
| **FastAPI / Starlette** | Custom `@app.exception_handler(RequestValidationError)` mapping Pydantic errors -> `errors[]` | FastAPI default `422` uses `{ "detail": [...] }` — normalize if adopting strict RFC 9457 across services |
| **Spring Boot 3+** | Native `org.springframework.http.ProblemDetail` (`spring.mvc.problemdetails.enabled=true`) | Ensure `server.error.include-stacktrace=never` in production |

## 6. Decision Matrix & Trade-Offs
| Error Scenario | Correct HTTP Status | Safe `detail` Example |
| :--- | :---: | :--- |
| Malformed JSON syntax | `400` | `"Request body is not valid JSON."` |
| Missing/expired bearer token | `401` | `"Authentication credentials are missing or invalid."` |
| Role lacks permission | `403` | `"You do not have permission to perform this action."` |
| Duplicate unique invoice number / version conflict | `409` | `"Resource state conflict; refresh and retry."` |
| Invalid email / negative quantity | `422` | `"One or more fields failed validation."` + `errors[]` |
| Unhandled DB connection failure | `500` / `503` | Generic message + `requestId` (never raw PG/ORM string!) |

## 7. Real Production Scenario
A global exception handler returns `res.status(500).json({ message: err.message, stack: err.stack })`. When a unique constraint fails on `users_email_key`, the API leaks internal table/column names and database driver versions to attackers (plus confirms email existence!). Replacing it with `buildProblemDetails` mapping known domain/DB errors to `409`/`422` and sanitizing all `5xx` responses eliminates information disclosure while keeping debugging instant via `requestId`.

## 8. Failure Modes & Edge Cases
- **WRONG:** Returning `400` or `500` for EVERY error, or wrapping errors inside HTTP `200 OK` (breaks CDN/proxy observability, retry policies, and client SDK error interceptors).
- **RIGHT:** Use accurate RFC 9110 status codes paired with `Content-Type: application/problem+json` (`RFC 9457`).
- **WRONG:** Returning `"Internal error"` without a `requestId`/`traceId` (support and SRE cannot correlate user screenshots to server logs).
- **RIGHT:** Always attach `requestId` in BOTH the JSON problem envelope and the `X-Request-Id` response header.

## 9. Testing & Verification
- Run `python shadow-api/scripts/api_contract_verifier.py --check-problem-json <error_fixture.json>`.
- Add integration tests forcing an unhandled exception and a DB unique-constraint error; assert HTTP `500`/`409`, `Content-Type: application/problem+json`, valid `requestId`, and zero stack/SQL substrings.

## 10. Operational Considerations
- Maintain a stable registry of problem `type` slugs (`validation-failed`, `idempotency-conflict`, `rate-limit-exceeded`) so frontend/mobile clients localize user messages cleanly by `code`/`type` without string-matching English prose.

## 11. Authoritative References
- IETF RFC 9457 — *Problem Details for HTTP APIs* (obsoletes RFC 7807, `https://www.rfc-editor.org/rfc/rfc9457.html`).
- IETF RFC 9110 — *HTTP Semantics* (`https://www.rfc-editor.org/rfc/rfc9110.html`).

## 12. Limitations & When NOT to Use
- Preserve an existing established brownfield API error envelope if active external consumers depend on it (never break live clients purely for RFC 9457 cosmetics); introduce RFC 9457 on new services or new major API versions (`v2`).
