---
name: handoff
description: "Save or load a cross-agent session handoff summary (Antigravity, Claude Code, Codex, Gemini CLI) when context/memory is full. Trigger with /handoff to save or '/handoff load' / 'lanjut handoff' to resume."
---

# /handoff — Cross-Agent Session Handoff (Shadow Army)

Use this skill whenever the **Monarch** invokes `/handoff` (or says `"handoff"` / `"lanjut handoff"`).
This skill connects directly to the **`shadow_handoff` MCP server** (`save_handoff`, `load_handoff`, `list_handoffs`).

## How to Execute

1. **Default (`/handoff` with no arguments, or `/handoff save`) — Save & Compact Current Session**:
   - Immediately call the `save_handoff` tool on the `shadow_handoff` MCP server (`d:/Ridhuan Ngoding Moment/SKILL/mcp-servers/shadow-handoff-mcp/index.mjs` if MCP is not yet reloaded in the current window) with:
     - `projectPath`: the active workspace directory path
     - `sourceAgent`: current agent name (`Antigravity`, `Claude Code`, `Codex`, or `Gemini CLI`)
     - `title`: short milestone title
     - `currentGoal`: the Monarch's active objective
     - `completedWork`: concise bullet list of verified completed tasks
     - `nextSteps`: ordered, actionable next steps for the next session
     - `keyDecisionsAndContracts`: verified contracts, strict types, and architectural decisions
     - `blockersOrBugs`: any open bugs or blockers
     - `importantFiles`: key file paths to inspect first
   - Report the saved handoff ID and file path concisely to the **Monarch**.

2. **Resume (`/handoff load`, `/handoff lanjut`, or `"lanjut handoff"`) — Load Latest Handoff**:
   - Immediately call the `load_handoff` tool on the `shadow_handoff` MCP server for the current `projectPath` (or globally if no project is open).
   - Present a brief 3-bullet summary of the loaded state to the **Monarch** and immediately proceed with Step 1 of `nextSteps`.

3. **History (`/handoff list`)**:
   - Call `list_handoffs` on the `shadow_handoff` MCP server and display the saved snapshots.
