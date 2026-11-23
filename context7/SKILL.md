---
name: context7
description: "Fetch real-time, version-accurate official documentation and code examples via Context7 MCP. Use when implementing or debugging library, framework, or SDK APIs where training knowledge may be outdated."
---

# /context7 — Live Official Documentation Lookup (Shadow Army)

Use this skill whenever the **Monarch** invokes `/context7` or when verifying latest framework/library syntax (Next.js, React, Tailwind CSS, NestJS, Prisma, Go, FastAPI, etc.).
This skill connects directly to the **`context7` MCP server** (`resolve-library-id`, `query-docs`).

## Version-matched workflow

1. Identify the workspace owning the import, its resolved lockfile or installed package metadata, the symbol, and runtime. A manifest range alone leaves the exact version unresolved. For local forks inspect the fork's exports, declarations and tests.
2. Resolve the maintainer's library ID and query the version matching the consumer. Record publisher, version or tagged revision, symbol and source URL. For a migration, compare old and target contracts and the migration guide.
3. Reproduce the call using the existing typecheck or a local fixture. If only another major is documented, restrict claims to what the installed code establishes and seek a tagged source. A question about an old version does not authorize an upgrade.
4. When the connector is unavailable, use installed docs, exported types or a pinned maintainer source. Mark unresolved runtime behavior. Hand off the evidence, affected caller and repeatable check.

## Scope & Evaluation
- **Keep-Lean Boundary:** Trigger ONLY for library/framework/SDK documentation lookups where version-accurate syntax matters; do NOT trigger for internal-only domain logic or auto-upgrade dependencies on a legacy-version question.
- **Evaluation Suite:** [evaluations.md](evaluations.md) (`python -m unittest discover -s context7/tests -v`).
