# TOKEN-EFFICIENCY — Shadow Monarch Doctrine: AI Token, Context & Execution Efficiency

Use when optimizing AI agent token consumption, minimizing context window bloat, orchestrating multi-turn tool calls,
delegating to subagents ("Shadow Army"), or designing token-efficient prompts and workflows.

## 1. The Shadow Monarch Mental Model (Mana = Context & Tokens)

Operate like the **Shadow Monarch** commanding a specialized **Shadow Army**:
- **The Monarch (Primary Context Window)**: holds only the mission objective, verified system contracts, active execution
  plan, and final verification state. Guard the primary context window fiercely — every unnecessary token loaded into
  the main conversation is re-billed and re-processed on **every subsequent turn**.
- **Shadow Generals (56 Relational `reference/*.md` Modules + 59 Modular Specialist Skills)**: domain, role, language, and sub-task knowledge tables plus skill-owned `references/01..NN-*.md` playbooks. Summon (**load**) only the exact Generals via `skill_router.py --route` (`companion_skills` -> `recommended_playbooks` / `## Reference Guide`); dismiss the rest.
- **Shadow Soldiers (Tools & Subagents)**: execute targeted reconnaissance (grep/search), parallel file edits, or noisy
  background research, returning only distilled, verified intelligence to the Monarch.

## 2. Foreign Key & 2-Step Playbook Loading Budget

Strictly bound how many `reference/*.md` files and specialist playbooks you load per task:
- **Tier 0 — Trivial / Factual Question** (*"what is HTTP 409?"*, *"bedanya HTTP 401 dan 403?"*, *"fix README typo"*): load **0 skills & 0 reference files**.
  Answer directly in 2–5 sentences.
- **Tier 1 — Single-Layer Edit or Bug Fix**: load **1 primary skill `SKILL.md` + 1–2 matched `references/*.md` playbooks** (via `recommended_playbooks`) and **0–2** `shadow-monarch/reference/*.md` files.
- **Tier 2 — Cross-Layer Feature or Architecture**: load **up to 4 companion skills + up to 4 playbooks/refs** total (`max_companion_skills = 4`).
- **Never pre-load unrelated language guides, UI `antislop*` bundles on pure backend/SQL/CLI tasks, or entire `references/` directories** "just in case".

## 3. Surgical Codebase Reconnaissance (Input Token Efficiency)

Reading entire files blindly is the #1 cause of context window exhaustion:
1. **Locate before reading**: use fast metadata/search tools (`grep_search`, `find_by_name`, symbol outline) to find the
   exact file path and line numbers where a route, DTO, component, or function is defined.
2. **Read narrow line slices**: view only the relevant line range (`StartLine` to `EndLine`, e.g., 50–120 lines around
   the target function) rather than dumping a 1,500-line file into context.
3. **Avoid redundant re-reads**: once a file slice is in recent context and has not been modified externally, do not call
   `view_file` on the exact same lines again.
4. **Filter noisy command outputs**:
   - Never run commands that dump thousands of lines (`cat huge.log`, `git log` without `-n`, verbose test suites without filters).
   - Scope commands tightly: `git log -n 5 --oneline`, `git diff --stat`, `npx tsc --noEmit`, or run only the single affected test file (`npx vitest run src/orders/order.service.spec.ts`).

## 4. Parallel Tool Execution (Turn & Prefix-Cache Efficiency)

Every extra agent turn resends the entire conversation history (input tokens = $\sum_{t=1}^{N} \text{context}_t$):
- **Batch independent tool calls in a single turn**:
  - If you need to inspect `controller.ts`, `service.ts`, and `schema.prisma`, call `view_file` on all three **in parallel in one turn** instead of 3 sequential turns.
  - When updating multiple independent files, issue the file-edit tool calls together where supported.
- **Surgical edits over full-file rewrites**:
  - Use targeted block replacement (`replace_file_content` on the exact changed lines) rather than rewriting a 600-line
    file from scratch (saves 80%+ output tokens and eliminates accidental deletion of unrelated code).

## 5. Subagent ("Arise") Delegation for Context Isolation

When a task requires reading 15+ files, exploring an unfamiliar legacy repo, or searching external docs/literature:
- **Spawn a bounded read-only subagent**: give it a strict prompt specifying the exact question to answer and the exact
  compact format to return (e.g., *"Find all callers of `calculateTax` and return a Markdown table of `File:Line | Caller | Contract` in under 250 words"*).
- All intermediate file dumps and dead-end searches stay isolated inside the subagent's disposable context; the Monarch
  receives only the 250-word verified summary.

## 6. High-Density Communication (Output Token Efficiency)

Output tokens are $3\times\text{--}5\times$ more expensive and slower to generate than input tokens:
- **Zero conversational filler**: skip preambles (*"Certainly! I'd be happy to help you with that..."*, *"Let's dive in!"*)
  and repetitive closing summaries. Start immediately with the answer, diagnosis, or action.
- **Do not echo large edited files in chat**: when you have already applied an edit to a file on disk using a tool,
  do not paste the entire 200-line file into the chat response. Summarize what changed, why, what dead code was cleaned,
  and link the file/lines (`[order.service.ts](file:///.../order.service.ts#L42-L68)`).
- **Scale response length to task complexity**:
  - Simple question → 1 short paragraph or 3–5 bullet points.
  - Bug fix / Refactor → Root cause + surgical file links + verification result.
  - Architecture / PRD / KAK → Structured tables and Mermaid diagrams (tables and diagrams convey 5x more structure per token than prose walls).
