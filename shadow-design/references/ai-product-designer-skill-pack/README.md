# AI Product Designer Skill Pack — standalone / no executable dependencies

This pack creates **one Agent Skills-compatible skill**, with self-authored references and templates. It contains Markdown only: no binaries, code execution hooks, dependencies, cloned repositories, fetched scripts, or preconfigured external MCP endpoints. The upstream repositories are references only, not copied source.

## Install (manual, non-executable)
1. Extract ZIP locally and inspect every file.
2. Copy folder `ai-product-designer/` to the skill directory of your agent:
   - Codex commonly uses `~/.agents/skills/ai-product-designer/` or a supported project-scoped skills location.
   - Claude Code commonly uses `~/.claude/skills/ai-product-designer/` or `.claude/skills/ai-product-designer/` in a project.
   Check your installed agent version's current supported paths.
3. Restart/reload the agent skill discovery if necessary.
4. Ask the agent: `Use ai-product-designer to design [feature] without implementing code.`
5. Or paste `MASTER-PROMPT.md` into your agent after pointing it to the local skill.

## Contents
- `MASTER-PROMPT.md`: copy/paste prompt for Codex/Claude Code.
- `ai-product-designer/SKILL.md`: official-style skill entrypoint + routing.
- `ai-product-designer/references/`: 11 original knowledge modules, including supply-chain/MCP safety.
- `ai-product-designer/templates/`: feature spec and UX review templates.

## Optional third-party integrations
Read `references/11-external-projects-and-trust.md`. Do not automatically install. Before adoption, review *specific version* for license, scripts, transitive dependencies, capabilities, credentials, data privacy, and MCP write permissions. Even an official MCP can have powerful editor privileges; a GitHub repository being public is not a security audit.

## Example requests
- `Use ai-product-designer. Design document upload + async indexing with Admin and Viewer roles; do not code.`
- `Use ai-product-designer to audit the existing proposal CRUD UX, preserving current design system.`
- `Use ai-product-designer to turn these user stories into Mermaid flows, screen/state matrices and UAT cases.`

## Validation
All content in this pack is authored for this request, based on general UX principles and linked upstream documentation; third-party skill bodies are not included. Review with a human for regulated or high-stakes products. Numeric UX review is a planning heuristic and not a user-tested score.
