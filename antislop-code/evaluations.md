# Antislop Code — Keep-Lean Filter Evaluation Suite

> Compact offline behavioral evaluation suite for `antislop-code`. Validates stripping decorative banners, obvious line narration, vague TODOs, and emoji clutter while strictly preserving non-obvious why-comments (security, concurrency, protocol invariants, legal notices) AND never altering executable code, imports, or control flow.

## Graded Scenarios

| ID | Scenario Prompt | Expected Specialist Behavior | Fail Red Flags |
| :--- | :--- | :--- | :--- |
| **ASCD-01** | *"Clean comments in `auth.ts` containing `// ======= MAIN LOGIC =======`, `// ✅ Step 1: Validate input`, `let count = 0; // Initialize count`, and `} // end if`."* | Strips decorative ASCII banners, decorative emoji comments, step narration, obvious-line narration, and closing-brace end markers without touching a single character of executable TypeScript logic. | Leaves decorative `=======` banners / `✅` comments, OR rewrites code logic while cleaning comments. |
| **ASCD-02** | *"Strip ALL comments from `webhookHandler.ts`, including `// Stripe retries webhooks for up to 72h; deduplicate strictly by event.id.` and the SPDX license header."* | Enforces **Not a Ban (Preserve Non-Obvious Why-Comments)**: keeps the Stripe retry/dedup invariant comment and legal/license header intact, removing ONLY filler/obvious comments. | Deletes security, concurrency, protocol-workaround, or license comments indiscriminately. |
| **ASCD-03** | *"Tighten a 6-line rambling comment that cites 3 Jira ticket IDs and a historical timeline just to explain why a `50ms` debounce protects Safari autofill."* | Fixes **The Over-Explained Comment**: condenses it to 1 concise sentence-case line stating strictly the Safari autofill constraint without historical storytelling or ticket padding. | Keeps a 6-line history essay OR deletes the constraint entirely so the next engineer breaks Safari. |
| **ASCD-04** | *"While cleaning comments in `orderService.ts`, also rename `calcTot()` to `calculateTotal()`, reorder imports, and simplify the `if/else` branch."* | Enforces the **Scope Guardrail**: modifies comments ONLY and leaves executable code, identifiers, imports, formatting, and control flow 100% untouched (route behavior-preserving code restructuring to `/shadow-refactor`). | Renames identifiers, reorders imports, or modifies control flow under a comment-hygiene pass. |
| **ASCD-05** | *"Replace `// TODO: Improve this` and `// Note: This is important` with cleaner versions."* | Removes empty labels and vague TODOs that name no actionable task (retaining a TODO ONLY when an existing concrete task + context is already specified). | Replaces vague TODOs with equally empty filler like `// TODO: Enhance performance later`. |

## Verification Status
- **Static & Validator Verification:** Verified locally via `python evals/validate_skill_evaluations.py`.
- **Live AST Diff Verification:** `NOT_RUN` (offline structural suite).
