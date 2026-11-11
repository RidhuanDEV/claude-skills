---
name: handoff
description: "Save, load, or merge cross-agent session handoffs (Antigravity, Claude Code, Codex, Gemini CLI) when context/memory is full or when parallel sessions must be combined into one agent. Trigger with /handoff to save, '/handoff load' / 'lanjut handoff' to resume, '/handoff merge' to combine parallel sessions."
---

# /handoff — Cross-Agent Session Handoff (Shadow Army)

Use this skill whenever the **Monarch** invokes `/handoff` (or says `"handoff"` / `"lanjut handoff"` / `"gabung handoff"`).
This skill connects directly to the **`shadow_handoff` MCP server** (`save_handoff`, `load_handoff`, `list_handoffs`, `merge_handoffs`).

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
     - `readinessLevel` (**required**): `PLANNED` (plan only) | `IMPLEMENTED` | `VERIFIED-LOCAL` | `REVIEWED` | `READY-TO-MERGE`, per the Rigor Protocol in `shadow-monarch`. Pick the level the evidence supports, not the one hoped for.
     - `untestedSurfaces` (**required**): surfaces not yet tested (e.g. "real multi-turn conversation", "topic switch", "ALL-CAPS input", "UI during streaming"). Send `[]` only if every surface was actually tested.
     - `claimEvidenceMap`: for each readiness claim, `{ claim, evidence, notMeasured }`.
     - `sessionLabel`: set when another session works on the same project in parallel (e.g. `plan`, `review`), so neither overwrites the other.
   - Report the saved handoff ID, readiness level, and file path concisely to the **Monarch**. If the result contains `mergeHint`, tell the Monarch that parallel sessions exist and offer `/handoff merge`.

2. **Resume (`/handoff load`, `/handoff lanjut`, or `"lanjut handoff"`) — Load Latest Handoff**:
   - Immediately call the `load_handoff` tool on the `shadow_handoff` MCP server for the current `projectPath` (or globally if no project is open).
   - **Read `untestedSurfaces` and `readinessLevel` before writing any review conclusion or readiness claim.** Treat listed surfaces as unverified; do not upgrade the readiness level without new evidence.
   - If the result contains `unmergedSessions`, the snapshot shows only one parallel session. Tell the Monarch and offer `/handoff merge` before continuing.
   - Present a brief 3-bullet summary of the loaded state to the **Monarch** and immediately proceed with Step 1 of `nextSteps`.

3. **Merge (`/handoff merge` or `"gabung handoff"`) — Combine Parallel Sessions Into One Agent**:
   - Typical case: session A saved with `sessionLabel: "plan"`, session B with `sessionLabel: "review"`; the Monarch wants one agent to continue.
   - Call `list_handoffs` with `projectPath` to see saved `sessions`, then `merge_handoffs` with `sessionLabels` in execution order (e.g. `["plan", "review"]`).
   - The merge keeps the **lowest** readiness level, unions untested surfaces, tags every item with its source session, and moves merged sessions to `sessions/archive/` (nothing is deleted).
   - Decisions from different sessions are listed side by side, not reconciled. Report every entry in `warnings` (different branches/commits, sessions >24h apart, possible contradictions) to the Monarch before acting on the merged steps.
   - Then proceed as in Resume.

4. **History (`/handoff list`)**:
   - Call `list_handoffs` on the `shadow_handoff` MCP server and display the saved snapshots and any unmerged `sessions`.
