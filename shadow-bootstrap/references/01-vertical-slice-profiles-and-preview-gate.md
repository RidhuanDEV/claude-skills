# 01 — Vertical-Slice Profiles, `preview_scaffold.py` & Conditional Infrastructure

## 1. Purpose & Activation Conditions
Scaffold the **smallest runnable, production-hygiene vertical slice** for a new `cli`, `static`, `worker`, `http`, or `library` target — previewing target safety first (`preview_scaffold.py`), preventing accidental overwrites of non-empty directories (`REVIEW_EXISTING`), and refusing unrequested infrastructure bloat (`Redis`, `Kafka`, `K8s`). Activate when initializing a brand-new project or new package inside a workspace.

## 2. Prerequisites
- Resolved product profile (`cli`, `static`, `worker`, `http`, `library`) and stack choice — if still material and unresolved, ask the Monarch via the interactive question tool BEFORE generating files!
- In a monorepo: inspected root workspace manifests (`pnpm-workspace.yaml`, `package.json`, `pyproject.toml`, `go.work`), sibling projects, package manager, local SDKs, and CI presets.

## 3. Technical Principles & Constraints
- **Preview-First Safety Gate (`preview_scaffold.py`):** ALWAYS run `python shadow-bootstrap/scripts/preview_scaffold.py TARGET --profile <profile> [--capability ...]` before invoking any generator.
  - If `TARGET` is non-empty, `preview_scaffold.py` returns **`REVIEW_EXISTING`** — STOP immediately, inspect existing files & provenance, and handle additions through the owning project's brownfield conventions (never blindly overwrite!).
  - On a retry after a partial/interrupted generator run, preserve existing work, diff against the preview, and resume ONLY attributable missing steps.
- **One Complete Vertical Slice Per Profile:**
  1. **`cli`:** 1 command, strict argument parser, documented input & `0`/`1` exit codes, 1 executable example + unit test.
  2. **`static`:** 1 semantic responsive accessible page (`antislop` + `modern-web-guidance`), reproducible production build, zero-CLS assets.
  3. **`worker`:** 1 idempotent job handler, explicit retry/DLQ semantics, structured logging, and a duplicate-delivery test.
  4. **`http`:** 1 validated request/response contract + matching smoke test, fail-fast startup env validation, non-blocking JSON structured logger (`pino`/`structlog`/`log/slog`/Monolog) with `X-Request-Id` + secret/PII redaction, and graceful `SIGTERM` shutdown (`03`).
  5. **`library`:** 1 typed public export (`exports` map, clean ESM/types), exercised by a consumer smoke test.
- **Conditional Infrastructure Only (Zero Day-1 Bloat!):**
  - Add DB/migrations ONLY when persistence is requested (with isolated test DB & replay check).
  - Add a queue ONLY when async durability is requested (with ack & retry ownership).
  - Add a cache ONLY when justified (with tenant isolation & invalidation).
  - Add Docker Compose, OpenAPI, cloud CI, or OTel collectors ONLY when selected or established by workspace convention — route unsettled API documentation choices to `/shadow-api` before creating competing specs!

## 4. Architecture & Implementation

### Greenfield Profile & Minimum Vertical Slice Matrix

| Profile | Official Generator Examples | Minimum Vertical Slice (Mandatory) | Conditional Add-Ons (ONLY When Requested) |
| :--- | :--- | :--- | :--- |
| **`cli`** | `npm init`, `uv init`, `cargo init`, `go mod init` | 1 command, strict arg parse, `0`/`1` exit codes, unit test | Shell completion, config loader |
| **`static`** | `npm create vite@latest`, `npm create astro@latest` | 1 responsive accessible page, reproducible build | Sitemap, search index, CSP headers |
| **`worker`** | `npm init` + TS (`tsx`/Node 22), `uv init` | 1 idempotent job, retry/DLQ contract, duplicate-delivery test | Queue broker (`PG SKIP LOCKED`/`BullMQ`), OTel |
| **`http`** | `create-next-app`, `nest new`, `fastify-cli`, `uv` FastAPI | 1 validated endpoint, structured JSON logger + `X-Request-Id` + redaction, graceful shutdown, smoke test | OpenAPI (`/shadow-api`), DB migrations, cache |
| **`library`** | `tsup`/`unbuild`, `uv init --lib`, `cargo init --lib` | Typed public entry export, consumer smoke test | Dual exports, SemVer `CHANGELOG.md` |

### Preview Gate CLI Execution (`L0_READ_ONLY`)
```powershell
# Preview exact deliverables and detect non-empty target safety BEFORE touching disk
python shadow-bootstrap/scripts/preview_scaffold.py ./services/billing-worker --profile worker --capability idempotency
python -m unittest discover -s shadow-bootstrap/tests -v
```

## 5. Platform/Vendor Variations
- **Monorepo New Package (`packages/foo` or `apps/bar`):** Match the parent workspace's exact package manager (`pnpm` vs `npm` vs `bun` vs `uv workspace`), root `tsconfig.base.json`, ESLint config, and shared internal SDK links (`workspace:*` or `file:../../sdk/...`) instead of generating a disconnected standalone lockfile!
- **Windows PowerShell Compatibility:** Ensure generated `package.json` scripts run cleanly on Windows AND Linux (avoid Unix-only `NODE_ENV=test ...` inline env syntax — use `cross-env` or framework config flags).

## 6. Decision Matrix & Trade-Offs

| Scaffolding Strategy | Speed & Accuracy | Overwrite Risk | Bloat Risk |
| :--- | :--- | :--- | :--- |
| **Preview -> Official CLI -> 1 Vertical Slice** | Fast, version-accurate | **Zero** (`REVIEW_EXISTING` guard) | **Zero** |
| **Hand-Typing Config Boilerplate From Memory** | Slow, outdated config flags | Medium | Low |
| **"Enterprise Starter Kit" With 12 Unused Services** | Bloated | High | **Extreme** (unused Kafka/K8s rot immediately) |

## 7. Real Production Scenario
An engineer asked for a tiny CSV-to-JSON CLI tool and received a hand-written boilerplate repo containing Docker Compose, Redis, Express, Swagger, and an outdated `tsconfig.json` that failed `tsc` on Node 22. Running `preview_scaffold.py --profile cli`, initializing via official `npm init` + `tsc --init`, wiring 1 strict CLI command + 1 unit test delivered a clean, zero-warning, 100%-tested binary in 3 minutes with zero unused infrastructure.

## 8. Failure Modes & Edge Cases
- **WRONG:** Ignoring `REVIEW_EXISTING` on a non-empty folder and passing `--force` to overwrite an existing developer's files.
  **RIGHT:** Stop on `REVIEW_EXISTING`, inspect provenance, and integrate cleanly with existing project conventions (or ask the Monarch for an empty target path).
- **WRONG:** Inventing a competing `swagger.yaml` during HTTP bootstrap when the team uses code-first OpenAPI or Postman collections.
  **RIGHT:** Defer unsettled API documentation architecture to `/shadow-api` (`discover_api_artifacts`).

## 9. Testing & Verification
- Run `python -m unittest discover -s shadow-bootstrap/tests -v` (`test_preview.py`).
- From a clean working directory, verify the scaffolded target's exact `install` + `build` + `test` + `smoke` commands succeed with exit code `0` before handoff.

## 10. Operational Considerations
- Compare actual created/modified paths against the `preview_scaffold.py` output and explicitly report any prerequisites, external installations, or unresolved side effects.

## 11. Authoritative References
- `shadow-bootstrap/scripts/preview_scaffold.py` & `tests/test_preview.py`.
- `shadow-monarch/reference/OFFICIAL-FIRST-DEPENDENCY-POLICY.md`.

## 12. Limitations & When NOT to Use
- Do NOT use `shadow-bootstrap` on mature brownfield applications just to add a new feature route — extend brownfield projects via `/shadow-architect` & existing module conventions!
- Never publish generated packages remotely, provision cloud infrastructure, or delete existing user files without explicit Monarch authority.
