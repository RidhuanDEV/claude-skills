# SA-API-DISCOVERY-001

## Baseline and scope

The repository started at `6c7b999`. Before edits, the API MCP completed its stdio handshake. The router passed 38 probes, the eval runner passed 48, the approval gate passed 16, and the repository quality gate passed.

The enhancement applies to repository-local API documentation discovery and authorized changes to the identified source. The shared toolchain protocol proposed for other skills remains future work.

## Discovery inventory and compatibility

| Evidence found | Classification | Update and verification |
| --- | --- | --- |
| Structured OpenAPI 3.x YAML/JSON, including local split references | Contract-first candidate. A supported configuration such as a Redocly `apis.*.root` identifies a declared input. | Update the verified contract or referenced source. The MCP can upsert compact OpenAPI 3.x. Use project tooling for split documents. |
| Swagger 2.0 with structured contract and metadata | Contract-first candidate | Use the current Swagger workflow. The MCP can audit it read-only. |
| NestJS, Express swagger-jsdoc, FastAPI, Django REST Framework with drf-spectacular, Laravel with L5-Swagger, Go with swaggo/swag, Spring Boot with springdoc-openapi, ASP.NET Core with OpenAPI integration | Code-first when a supported integration or generator entry point corroborates the dependency or import | Update the repository declarations. Regenerate through the established permitted workflow and audit the result. Dependency-only matches appear as hints. |
| A package script that calls a local JS/TS writer, which serializes an imported OpenAPI builder to a literal path | Code-first repository generator when the builder provides an OpenAPI version and paths | Trace the builder and any referenced endpoint registry. Use the declared generate and check scripts. Inspect the literal output directly when it is in an ignored build directory. |
| TypeSpec declarations and literal OpenAPI emitter output configuration | Contract-first declaration, with a generated OpenAPI output when the config links it to a file | Update TypeSpec using the project's compiler/emitter. Verify the emitted contract without manually upserting it. |
| Structured AsyncAPI with channels or operations, GraphQL root operations or introspection settings, Protobuf service with RPC declarations | Separate AsyncAPI, GraphQL and gRPC protocol evidence | Validate with the owning protocol's tooling. GraphQL introspection configuration indicates presence and needs additional ownership evidence. |
| Swagger UI, Scalar, Redoc, or RapiDoc configuration | Viewer. Literal inputs can resolve to a local file, a known generator endpoint, an external URL, or an unresolved path. | Trace the viewer input to its owner. Refresh or verify the downstream rendering through the existing workflow. |
| Markdown with API headings and HTTP examples | Supplementary documentation. Markdown alone can support a documentation-first workflow. | Confirm ownership and preserve Markdown when suitable. Resolve a machine-readable contract choice only when needed. |
| Postman, Bruno, Insomnia, Hoppscotch, Thunder Client, `.http` or `.rest` | Client collection or client environment | Confirm the mapping to the service before using the native workflow or targeted edits. Preserve existing request tests, examples, auth and environment values. |
| Generated header, structured generation flag, recognized command output, or explicit TypeSpec emitter output | Generated artifact | Update its owning source. Compare or regenerate the output through the existing workflow. |
| Same-protocol candidate sources with unclear ownership | `CONFLICT_REQUIRES_DECISION` | Scope discovery to the service or resolve the relationship before changing either source. |
| Incomplete scan, unknown tool, unresolved viewer input or unclear workflow | `UNKNOWN` | Inspect the project's real workflow and permissions. Incomplete scans block MCP OpenAPI writes. |
| Explicit compatible selection in a service without competing documentation | `COMPATIBLE` for supported OpenAPI 3.1 contract-first YAML or JSON selection | Honor the selected path and approach. The write tool requires `allowNewSpec: true`. |
| Protocol/format mismatch or destination outside the project | `INCOMPATIBLE` | Resolve the mismatch before initializing documentation. |

`PARTIALLY_COMPATIBLE` describes existing repository evidence when runtime and toolchain compatibility still need verification.

## Ownership contract

`discover_api_artifacts` takes an owning `projectRoot`, optional `targetProtocol` and optional explicit `selection` with protocol, format, location and approach. It retains the previous OpenAPI and collection fields. The added result includes status, architecture, framework, protocol inventory, `sourceOfTruth`, `systems`, viewers, generated artifacts, collections, dependency hints, conflicts, unresolved references, compatibility, decision and scan coverage. Paths in the new fields are relative to the owning project.

The artifact roles are `AUTHORITATIVE_SOURCE`, `GENERATED_ARTIFACT`, `DOCUMENTATION_VIEWER`, `CLIENT_COLLECTION`, `SUPPLEMENTARY_DOCUMENTATION` and `UNKNOWN`. A structurally valid standalone contract can be an ownership candidate with `sourceOfTruth.verified: false`. A supported generator integration or explicit configured source strengthens confidence at repository level. A same-protocol conflict makes the affected candidates unknown and clears source selection for that protocol. Multiple independently owned protocols can produce `HYBRID`.

Generator evidence includes actual entry paths, dependency manifests, explicit output paths or endpoints when detectable, and script names or line locations. Inspect the complete declaration in the repository before invoking it. Discovery issues no network requests, runs no commands and writes no files. The skill instructs the agent to review dependencies, environment, authorization, validation, versioning, auth documentation, compatibility, generated outputs and file diffs before running an established workflow.

The OpenAPI write tools protect recognized generated outputs, conflicts, unresolved owners and cross-project locations. Bulk upsert performs no collection writes. `sync_postman_collection` only initializes a new collection with explicit intent and protects existing assets. Existing collections follow their project workflow. `validate_openapi_spec` performs a read-only operation and local-reference audit. `compare_openapi_drift` compares two local snapshots for missing, unexpected and changed operations and named schemas. It accepts explicit internal route exclusions and respects `x-internal`.

## Changed files

| Path | Change |
| --- | --- |
| `mcp-servers/shadow-api-mcp/index.mjs` | MCP discovery contract, bounded scan, write guards, read-only validation, drift tool and collection protection |
| `mcp-servers/shadow-api-mcp/discovery.mjs` | Evidence extraction, framework and artifact classification, protocol scoping and decisions |
| `mcp-servers/shadow-api-mcp/repository-generators.mjs` | Static tracing of repository-owned writers, source declarations, outputs and registry-backed viewers |
| `mcp-servers/shadow-api-mcp/discovery.test.mjs` | Isolated realistic fixtures exercised through JSON-RPC stdio |
| `shadow-api/SKILL.md` | Ownership-based authorization, update, synchronization and verification instructions |
| `shadow-monarch/SKILL.md`, `shadow-monarch/GLOBAL.md` | Replacement policy for endpoint work and greenfield intent |
| `shadow-monarch/scripts/skill_router.py` | API documentation routing and positive/negative probes |
| `shadow-monarch.zip` | Rebuilt and byte-verified against 65 tracked skill sources, excluding the previously packaged Python cache |
| `reports/shadow-enhancement/SA-API-DISCOVERY-001/implementation-summary.md` | Inventory, compatibility, verification, limitations and rollback |

## Verification

| Command or check | Status | Evidence |
| --- | --- | --- |
| `node --test mcp-servers/shadow-api-mcp/discovery.test.mjs` | PASS | 38/38 fixture tests. Includes active, passive and disabled integrations, local and external viewer inputs, marked and configured generated outputs, greenfield with and without intent, conflicting owners, preservation of custom collections, project and junction boundaries, drift and a bounded source-to-output synchronization fixture. The repository-writer regression covers missing output, misleading script names and mismatched viewers. |
| `python shadow-monarch/scripts/skill_router.py --self-test` | PASS | 40/40 probes. API documentation ownership routes to `shadow-api`. A generic source-of-truth question does not. |
| `python evals/run_evals.py --self-test` | PASS | 48/48 existing deterministic eval probes. |
| `python shadow-monarch/scripts/execution_approval_gate.py --self-test` | PASS | 16/16 authorization probes. |
| `python shadow-quality/scripts/shadow_gate.py --repo . --check-docker-leaks --probes-verified` | PASS | No blocking violations and zero leaked test containers. |
| Archive integrity and source comparison | PASS | All 65 tracked archive entries matched the workspace source bytes. |
| Real repository discovery and `npm run api-docs:check` in `my-apu` | PASS | Identified the Express endpoint registry and OpenAPI builder as code-first sources, `dist/docs/openapi.json` as output, and `/docs/openapi.json` as the Swagger UI input. The project check passed against the existing artifact. |
| Live framework servers, native third-party generators, load, global installation and release | NOT_RUN | MCP verification used Windows, Node 24.22.1, Python 3.13.3, isolated fixtures, and the real repository check listed above. |

## Known limitations

- Static detection uses recognized patterns. Dynamic or aliased generator calls, custom tooling, interpolated paths, build-only output directories, runtime flags and ownership shared across service roots may need repository inspection. The scanner excludes dependency/build directories and sample/test ownership evidence. It bounds depth at 12, files at 12,000, source evidence at 256 KiB per file and collected evidence at 32 MiB.
- Repository script tracing covers direct Node, tsx or ts-node commands, named local imports, a JSON write with a literal destination and a supported route registry binding. Other script runners and dynamically resolved destinations need manual verification.
- GraphQL, gRPC and AsyncAPI detection identifies architecture. Protocol-specific validation and generation remain with the project's existing tools.
- OpenAPI drift checks are structural comparisons of supported fields. They can report formatting-independent changes in schema objects and operation data, but they do not prove semantic equivalence between differently bundled contracts, validate all OpenAPI keywords, or exercise the live API. Remote references and unsupported local pointers make comparison unverified.
- Integration choices for existing modular files, Swagger 2.0 and user-authored collections deliberately use project workflows. Existing automation that relied on implicit greenfield creation, bulk Postman replacement, direct updates to split roots, or validation rewriting masters must use the explicit ownership-based workflow.

## Rollback

Revert the enhancement changes as a unit to restore the previous MCP writer and skill contract together. Restore the package from the same baseline as the skill sources. The change adds no dependency, database migration, global state migration or external publication. Verify the restored MCP handshake and router baseline before using the previous workflow.
