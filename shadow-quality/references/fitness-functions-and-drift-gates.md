# Architectural Fitness Functions, Strict Typing & Drift Gates

> Use this playbook when enforcing strict compiler settings, ESLint module-boundary fitness rules, brownfield convention preservation, dead-code elimination, or executing deterministic rigor gates (`shadow_gate.py`).

## 1. Core Concepts
Code review comments don't scale alone; **executable fitness functions** turn architectural & type safety rules into fast automated checks:
- **Strict Type Boundaries:** Disallow implicit `any`, unsafe typecasts (`as Type`, `<Type>`), and non-null assertions (`!`) so invalid states fail at compile time instead of production runtime.
- **Brownfield Drift Control:** Measure new changes against the existing repository's folder layout, error format, logger, and internal SDK contracts rather than inventing competing patterns.

## 2. Technical Rules & Decision Matrix

| Quality Layer | Automated Mechanism | What It Catches |
| :--- | :--- | :--- |
| Compiler Rigor | Hardened `tsconfig.json` (`strict`, `noUncheckedIndexedAccess`) | Nullable index access bugs, implicit `any`, unhandled switch returns |
| Module Boundaries & Hygiene | ESLint `no-restricted-imports` + `no-console` | Cross-module internal DB coupling, stray debug prints in backend routes |
| Rigor, Secrets & Container Leaks | `python shadow-quality/scripts/shadow_gate.py --repo . --check-docker-leaks` | Type casts, `!` assertions, exposed secrets, leftover `*-test-*` Docker containers |
| Code Review Mode | Strictly `L0_READ_ONLY` inspection with `CRITICAL..NIT` severity | Unrequested mutations during review, logic/N+1/concurrency bugs, dead code |

## 3. Implementation Examples

### Strict `tsconfig.json` + ESLint Architectural Boundary Rule
```json
{
  "compilerOptions": {
    "strict": true,
    "noUncheckedIndexedAccess": true,
    "exactOptionalPropertyTypes": true,
    "noImplicitOverride": true,
    "noImplicitReturns": true,
    "noFallthroughCasesInSwitch": true,
    "skipLibCheck": true
  }
}
```
```js
// eslint.config.mjs (flat config excerpt enforcing module facade boundaries)
export default [
  {
    rules: {
      "no-restricted-imports": [
        "error",
        {
          patterns: [
            {
              group: ["../**/internal/*", "../../modules/*/internal/**"],
              message: "Import only from the target module's public facade (public.ts).",
            },
          ],
        },
      ],
      "@typescript-eslint/no-explicit-any": "error",
      "@typescript-eslint/consistent-type-assertions": ["error", { assertionStyle: "never" }],
    },
  },
];
```

### Deterministic Repository Rigor Gate
```powershell
python "shadow-quality/scripts/shadow_gate.py" --repo . --check-docker-leaks --probes-verified
```

## 4. Best Practices
- Aim for single-responsibility functions with shallow nesting and cyclomatic complexity `<= 10`; extract early returns and narrow guards when complexity creeps up.
- Pair every dead-code cleanup pass (unused exports, props, types, stale feature flags) with immediate typecheck + unit test verification.
- Keep findings actionable during review: cite exact `file:line`, explain the concrete failure scenario, and provide the smallest clean replacement patch.

## 5. Anti-Patterns (`WRONG` vs `RIGHT`)
- **WRONG (Silencing the compiler with casts or `@ts-ignore`):** Writing `const user = payload as AdminUser;` or `process.env.JWT_SECRET!` to appease `tsc`.
  **RIGHT:** Validate untrusted payloads with explicit schema/type predicates (`Zod` or manual runtime guards) and validate required env vars at process startup.
- **WRONG (Modifying files during an `L0_READ_ONLY` review or keeping competing utilities):** Editing code without review authorization, or adding a second logger/HTTP client beside the repo's established helper.
  **RIGHT:** Keep code reviews read-only unless edits were requested, and enforce reuse of existing repo utilities and local SDKs.

## 6. Production Considerations
- **CI Readiness Distinction:** Never declare `READY-TO-MERGE` unless strict typecheck, lint, test suites, and `shadow_gate.py` all ran *after* the final edit and reported `0` violations — list anything unverified honestly under `Not measured`.
- **Docker Cleanup:** Enforce `--rm --label shadow.ephemeral=true` and `try/finally` removal around ephemeral test DB containers so CI agents never accumulate leaked volumes.
