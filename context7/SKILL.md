---
name: context7
description: "Fetch real-time, version-accurate official documentation and code examples for any library or framework using the Context7 MCP server. Trigger with /context7."
---

# /context7 — Live Official Documentation Lookup (Shadow Army)

Use this skill whenever the **Monarch** invokes `/context7` or when verifying latest framework/library syntax (Next.js, React, Tailwind CSS, NestJS, Prisma, Go, FastAPI, etc.).
This skill connects directly to the **`context7` MCP server** (`resolve-library-id`, `query-docs`).

## Workflow

1. Call `resolve-library-id` on the `context7` MCP server with the library/package name and query to get the exact Context7-compatible library ID.
2. Call `query-docs` with that `libraryId` and the specific technical question or API symbol to retrieve current official documentation and code examples.
3. Apply the verified official syntax directly to the **Monarch's** codebase without guessing from outdated training weights.
