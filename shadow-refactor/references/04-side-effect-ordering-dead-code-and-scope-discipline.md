# 04 — Side-Effect Ordering Preservation, Scoped Dead-Code Cleanup & `L1`/`L2` Boundaries

## 1. Purpose & Activation Conditions
Guard the three easiest ways a "clean" refactor silently breaks production or bloats a PR — **accidental side-effect reordering (DB commit vs webhook/email/cache)**, **leaving behind orphaned dead code (or deleting dynamic/reflection callers)**, and **scope creep into untouched files (`L2_SCOPE_EXPANSION`)**. Activate during every refactor execution and pre-merge diff review.

## 2. Prerequisites
- Locked Invariant Ledger (`01`) listing side-effect sequence and exact `allowed_scope_files` for the requested refactor.

## 3. Technical Principles & Constraints
- **Preserve Exact Side-Effect Ordering (`DB_COMMIT -> CACHE_INVALIDATE / EVENT_PUBLISH`):**
  - Never replace sequential `await ports.saveAndCommit(id); await ports.enqueueWebhook(id);` with `await Promise.all([...])`! Running them concurrently sends customer webhooks or deletes cache keys **before** the DB transaction commits (or even when the DB transaction rolls back!).
  - Record and assert exact call sequence (`events: ['db.commit', 'cache.unlink', 'outbox.notify']`) in characterization tests (`shadow-git/tests/test_worktree_semantic_order.py`)!
- **Scoped Dead-Code Elimination (Clean Modified Files Only!):**
  - During every refactor, actively delete newly orphaned helpers, unused types, unused props, unused imports, and unreachable branches **strictly inside the refactored scope** (`Rule 3`).
  - **Dynamic Caller Caution:** Before deleting an exported symbol or route handler, grep the entire workspace (including templates, dynamic `import()`, webhook dispatch tables, DI strings, and frontend callers!) so you don't delete something invoked dynamically!
  - Never leave commented-out "just in case" code blocks (`// old implementation...`) — Git history preserves every prior line cleanly!
- **Zero Collateral Scope Creep (`L1` vs `L2` Execution Boundary):**
  - Refactoring strictly inside explicitly requested modules with passing characterization tests = **`L1_SAFE_VERIFICATION`**.
  - Reformatting 25 unrelated files, renaming shared utilities outside requested scope, or opportunistically swapping dependencies/local SSO SDKs = **`L2_SCOPE_EXPANSION`** (blocked by `refactor_characterization_gate.py` `out_of_scope` check unless explicitly approved by the Monarch!).
- **Strict TypeScript Parity (`0 any`, `0 as Type`, `0 !`):** Never introduce `as any` or `!` non-null assertions as shortcuts when extracting typed helpers — tighten types cleanly at the boundary while preserving runtime behavior.

## 4. Architecture & Implementation

```ts
// Strict TypeScript Side-Effect Ordering Guard & Sequence Assertion Test (0 any, 0 casts)
export interface OrderCompletionPorts {
  readonly saveAndCommit: (orderId: string) => Promise<void>
  readonly invalidateCache: (orderId: string) => Promise<void>
  readonly enqueueWebhook: (orderId: string) => Promise<void>
}

export async function completeOrderPreservingOrder(
  ports: OrderCompletionPorts,
  orderId: string,
): Promise<void> {
  // Invariant: DB commit MUST finish BEFORE cache invalidation or external webhook notification!
  await ports.saveAndCommit(orderId)
  await ports.invalidateCache(orderId)
  await ports.enqueueWebhook(orderId)
}

export async function verifySideEffectOrderingInvariant(): Promise<void> {
  const observedOrder: string[] = []
  await completeOrderPreservingOrder(
    {
      saveAndCommit: async () => { observedOrder.push('db.commit') },
      invalidateCache: async () => { observedOrder.push('cache.invalidate') },
      enqueueWebhook: async () => { observedOrder.push('webhook.enqueue') },
    },
    'ord_42',
  )
  const expected = 'db.commit>cache.invalidate>webhook.enqueue'
  if (observedOrder.join('>') !== expected) {
    throw new Error(`SIDE_EFFECT_ORDER_BROKEN: got ${observedOrder.join('>')}, expected ${expected}`)
  }
}
```

### Scoped Refactor Diff Hygiene Checklist

| Diff Audit Check | Pass Criterion | Failure Sign |
| :--- | :--- | :--- |
| **File Scope Boundary** | `changed_files <= allowed_scope_files` | Unrequested edits in unrelated modules (`L2` violation) |
| **Side-Effect Sequence** | `DB_COMMIT` precedes cache/event/webhook calls | `Promise.all` mixing DB write + external side effect |
| **Dead Code in Modified Files** | `0` unused imports, helpers, types, commented-out blocks | Orphaned `legacyHelperOld()` or commented code left behind |
| **Dependency & SDK Parity** | `0` unsolicited library swaps; local SSO SDKs preserved | Replacing `file:../sdk/sso-client` or swapping ORM |
| **Static Quality & Types** | `tsc --noEmit` clean, `0 any`, `0 as Type`, `shadow_gate.py` PASS | Added `as unknown as Type` cast to silence compiler |

## 5. Platform/Vendor Variations
- **AST-Safe Automated Refactors (`ts-morph`, `ruff --fix`, `gofmt`/`gopls`, `rector`):** For mechanical symbol renames or import cleanups across a scoped module, prefer language-server / AST-aware refactoring tools over brittle global regex search-and-replace (which corrupts comments, strings, and SQL column names!).
- **React Component Refactors:** Watch `useEffect` dependency arrays and hook call order carefully — extracting sub-components or moving hooks conditionally breaks React's Rules of Hooks or introduces subtle infinite re-render loops!

## 6. Decision Matrix & Trade-Offs

| Cleanup Observation | Action Inside Current Refactor (`L1`) | Defer to Separate Ticket (`L2`) |
| :--- | :--- | :--- |
| **Unused import/helper inside target file** | Delete immediately & verify tests | — |
| **Messy unrelated file discovered nearby** | Leave untouched! | Record note & ask Monarch for separate `L2` scope |
| **Genuine domain bug spotted in target file** | Keep behavior identical in refactor step | Fix explicitly in separate Red-Before/Green-After commit (`/shadow-debug`) |

## 7. Real Production Scenario
During a cleanup of `src/orders/complete.ts`, a developer "optimized" three `await` lines into `Promise.all([db.commit(), redis.unlink(), webhook.send()])`, plus ran Prettier across 42 untouched files. Two bugs occurred immediately: failed DB transactions still fired `"order.paid"` webhooks to external partners, and the 42-file formatting diff hid the 3-line ordering bug from code reviewers! Enforcing `verifySideEffectOrderingInvariant()`, strict `allowed_scope_files` checks via `refactor_characterization_gate.py`, and keeping diffs laser-scoped prevented both regressions completely.

## 8. Failure Modes & Edge Cases
- **WRONG:** Deleting an exported function without checking dynamic string references (e.g., Next.js route exports `GET`/`POST`, Express dynamic router loaders, GraphQL resolvers, or external package consumers).
  **RIGHT:** Grep symbol names + framework entrypoints across the entire workspace before deleting exports; for public library exports, follow `/shadow-compat` deprecation rules!
- **WRONG:** Running `prettier --write .` across the entire repo inside a targeted 2-file refactor PR.
  **RIGHT:** Format ONLY the modified lines/files matching existing repository lint rules.

## 9. Testing & Verification
- Run `python shadow-refactor/scripts/refactor_characterization_gate.py --verify-plan plan.json` and `python shadow-quality/scripts/shadow_gate.py --repo .`.
- Run `git diff --stat` before reporting completion to verify every modified file belongs strictly inside the approved refactor scope.

## 10. Operational Considerations
- Include a concise **Dead Code Removed** bullet list and **Rollback Command** in every refactor handoff summary.

## 11. Authoritative References
- Martin Fowler — *Refactoring (2nd Ed.)* — Small Steps & Behavior Preservation.
- `shadow-refactor/scripts/refactor_characterization_gate.py` & `shadow-quality/scripts/shadow_gate.py`.

## 12. Limitations & When NOT to Use
- Do NOT use `shadow-refactor` to silence linter errors via `// eslint-disable` or `@ts-ignore` — resolve the underlying structural/typing issue cleanly or defer with an explicit tracked ticket.
