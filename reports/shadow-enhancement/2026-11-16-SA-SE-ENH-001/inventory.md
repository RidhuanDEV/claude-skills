# Phase 0 — Repository Inventory (`SA-SE-ENH-001`)

- **Run ID:** `2026-11-16-SA-SE-ENH-001`
- **Inspected Date:** `2026-11-16T11:54:45+07:00`
- **Repository Root:** `D:\Ridhuan Ngoding Moment\SKILL`
- **Git Branch & SHA:** `main` -> `origin/main` (`185c42a2fa8e520293b3819a56b681fd60b9fe18`, clean working tree)

## 1. Verified Baseline Counts
- **Skill Directories:** `45` (all contain `SKILL.md` with valid frontmatter and `<= 407` lines)
- **`shadow-monarch/reference/` Modules:** `53`
- **Custom MCP Servers (`mcp-servers/`):** `3` (`shadow-api-mcp`, `shadow-db-mcp`, `shadow-handoff-mcp`)
- **Evaluation Scenarios (`evals/evals.json`):** `28`

## 2. MCP Server Tool Contracts
| Server | Entrypoint | Exposed Tools | Read/Write Semantics |
|---|---|---|---|
| `shadow-api-mcp` | `mcp-servers/shadow-api-mcp/index.mjs` | `test_api_endpoint`, `upsert_openapi_endpoint`, `bulk_upsert_openapi_endpoints`, `sync_postman_collection`, `validate_openapi_spec`, `run_api_collection` | Writes OpenAPI/Postman files in target workspace; executes HTTP requests when target server runs |
| `shadow-db-mcp` | `mcp-servers/shadow-db-mcp/index.mjs` | `inspect_database_schema`, `run_readonly_query`, `generate_dbml_and_erd`, `compare_database_schemas`, `generate_cross_db_etl_and_warehouse` | Read-only SQL inspection against configured DSN; generates local DBML/Mermaid/ETL files |
| `shadow-handoff-mcp` | `mcp-servers/shadow-handoff-mcp/index.mjs` | `save_handoff`, `load_handoff`, `list_handoffs`, `merge_handoffs` | Reads/writes structured session state snapshots with `readinessLevel` and `untestedSurfaces` |

## 3. Starting Skill Inventory & Executable Scripts (`45` Skills)
- **Core (3):** `shadow-monarch` (`313` lines, `scripts/skill_router.py` + `consulting-core/scripts/consulting_core.py`), `handoff` (`44` lines), `context7` (`15` lines)
- **Anti-Slop (6):** `antislop` (`373` lines + `references/MANDATORY-RULES-R01-R40.md`), `antislop-ui` (`344` lines), `antislop-layoutmobile` (`170` lines), `antislop-human` (`204` lines + `contrast-check.py`, `contrast-mcp.py`), `antislop-copywriting` (`407` lines), `antislop-code` (`128` lines)
- **Discovery & Architecture (5):** `shadow-discovery` (`74` lines), `shadow-architect` (`93` lines), `shadow-plan` (`63` lines), `shadow-bootstrap` (`50` lines), `shadow-design` (`146` lines + T1 designer/UX research packs)
- **App & Data (7):** `shadow-auth` (`46` lines), `shadow-data` (`53` lines), `shadow-db` (`42` lines), `shadow-api` (`22` lines), `shadow-cache` (`51` lines), `shadow-integrate` (`45` lines), `shadow-accessibility` (`60` lines)
- **Quality & Release (11):** `shadow-quality` (`69` lines, `shadow_gate.py`, `codebase_intelligence.py`, `skill_vendor_sync.py`), `shadow-test` (`79` lines), `shadow-eval` (`52` lines, `ai_eval_gate.py`), `shadow-sec` (`50` lines), `shadow-privacy` (`61` lines, `privacy_pdp_auditor.py`), `shadow-perf` (`54` lines, `openapi_to_k6_scaffold.mjs`), `shadow-uat` (`60` lines), `shadow-release` (`51` lines), `shadow-compat` (`45` lines), `shadow-browser` (`19` lines), `shadow-mobile` (`49` lines, `mobile_release_gate.py`)
- **Ops & Maintenance (5):** `shadow-ops` (`44` lines + 7 reference docs + 8 OWASP/H5BP vendor sheets), `shadow-observe` (`42` lines), `shadow-finops` (`41` lines, `finops_cost_auditor.py`), `shadow-resilience` (`38` lines), `shadow-maintain` (`50` lines)
- **Delivery & Docs (3):** `shadow-handover` (`50` lines), `shadow-doc` (`134` lines, `doc_scaffold.py`, `reference_verifier.py`, `v2_core.py`, `v2_renderers.py`, `v2_acceptance.py`), `shadow-git` (`119` lines, `git_orchestrator.py`)
- **Enterprise Consulting (5):** `shadow-presales` (`37` lines, `presales_commercial_engine.py`), `shadow-grc` (`41` lines, `grc_assurance_engine.py`), `shadow-modernize` (`35` lines, `modernize_forensics_engine.py`), `shadow-pmo` (`36` lines, `pmo_governance_engine.py`), `shadow-ea` (`33` lines, `ea_portfolio_engine.py`)
