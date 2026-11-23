# 03 — Dependency, Framework & Runtime Upgrade Assurance

## 1. Purpose & Activation Conditions
Execute major/minor dependency, ORM, framework, and language runtime upgrades (`Node 20->22`, `Python 3.11->3.13`, `React/Next/Tailwind`, `Prisma/SQLAlchemy`, `Go/Rust`) **without breaking production builds, native binary addons, or transitive contracts**. Activate whenever upgrading packages in `package.json`, `pyproject.toml`, `composer.json`, `go.mod`, or `Cargo.toml`.

## 2. Prerequisites
- Clean green baseline test suite (`/shadow-test`) and locked manifest (`package-lock.json`, `pnpm-lock.yaml`, `uv.lock`, `go.sum`, `Cargo.lock`).
- Access to official changelogs/migration guides via `/context7` MCP or official release notes.

## 3. Technical Principles & Constraints
- **Audit Official Migration Guides FIRST (`/context7`):** Never rely on outdated model memory for breaking changes in Next.js, Tailwind v4, React 19, Pydantic v2, Zod v4, or SQLAlchemy 2 — fetch exact version-specific migration guides before editing `package.json`!
- **One Ecosystem Group Per Verified Step (Never 40 Majors in 1 Blind PR!):**
  - Upgrade cleanly in isolated, revertible waves: (1) Runtime/toolchain -> tests green -> (2) DB driver/ORM -> tests green -> (3) Core framework -> tests green -> (4) UI/auxiliary libs -> tests green.
  - If a bug appears, you immediately know which 1 dependency caused it!
- **Production OS, Architecture & C-Library Parity (`amd64`/`arm64`, `glibc`/`musl`):**
  - Packages with native bindings (`sharp`, `bcrypt`, `argon2`, `better-sqlite3`, `esbuild`, `swc`, `cryptography`, `psycopg2`) work on Windows/macOS dev laptops yet crash at container boot on `linux/arm64` or Alpine `musl`! Always verify prebuilt binary support and test builds inside the exact target production Docker base image!
- **Pin Resolved Versions & Preserve Internal/Local SDKs (`OFFICIAL-FIRST-DEPENDENCY-POLICY.md`):**
  - Inspect metadata non-destructively (`npm view <pkg> version engines peerDependencies maintainers`) BEFORE installing.
  - Check `engines` and `peerDependencies` compatibility (zero `--legacy-peer-deps` masking real runtime mismatches!).
  - Pin concrete versions in regulated/production projects and NEVER replace trusted local/internal SDKs (`file:../sdk/sso-client`) with unverified registry packages.

## 4. Architecture & Implementation

### Pre-Upgrade Non-Destructive Inspection Commands (`L0`)
```powershell
# Inspect Node package metadata, engines, peerDeps & dist-tags WITHOUT installing
npm view zod@4 version engines peerDependencies maintainers dist-tags --json

# Audit outdated packages safely without mutating node_modules
npm outdated
pip list --outdated
go list -m -u all
```

### Incremental Ecosystem Upgrade Sequence Matrix

| Upgrade Wave | Example Packages | Primary Regression Risk | Required Verification Gate |
| :--- | :--- | :--- | :--- |
| **1. Runtime & Compiler** | Node `20->22`, Python `3.11->3.13`, TypeScript `5.x` | Native addons, OpenSSL/TLS ciphers, strict type checks | Full build + Docker target image build + unit suite |
| **2. Data & Auth Core** | `pg`/`prisma`/`sqlalchemy`, `jose`/`passport` | Query dialect, Decimal/Date serialization, JWT alg defaults | Real-DB integration tests + `/shadow-auth` policy matrix |
| **3. Web Framework** | Next.js, Fastify, FastAPI, Laravel | Middleware order, cookie/CORS headers, SSR hydration | Route contract tests + `/shadow-browser` smoke check |
| **4. UI & Build Tooling** | React, Tailwind v4, Vite, PostCSS | CSS preflight resets (`cursor: pointer`!), bundle chunking | Visual/responsive `375px`/`1440px` check + `shadow_gate.py` |

## 5. Platform/Vendor Variations
- **Tailwind CSS v3 -> v4 Gotcha:** Tailwind v4 removes `cursor: pointer` on `<button>` in preflight, replaces `tailwind.config.js` with CSS `@theme`, and changes shadow/ring utilities — always verify interactive button cursor states and visual snapshots after upgrading!
- **Node.js ESM vs CommonJS Dual-Package Hazard:** Upgrading a transitive dependency that went ESM-only (`chalk`, `nanoid`, `p-limit`) breaks CommonJS (`require()`) apps at runtime if `tsup`/bundler settings aren't verified! Check `"type": "module"` and `"exports"` via `npm view <pkg> exports` first.
- **Python `uv` / `poetry` / `pip` Lockfiles:** Always regenerate lockfiles (`uv lock` / `poetry lock`) and test `uv sync --frozen` inside the target Linux Python image so platform-specific wheels (`manylinux` vs `musllinux`) resolve cleanly.

## 6. Decision Matrix & Trade-Offs

| Upgrade Tactic | Risk of Mystery Breakage | Rollback Effort | Recommendation |
| :--- | :--- | :--- | :--- |
| **Single-PR "Upgrade Everything" (`ncu -u`)** | **Very High** | Painful (all-or-nothing) | **AVOID** |
| **Grouped Incremental Upgrades + Lockfile Pin** | **Low** | Instant `git revert` per group | **Default** |
| **Masking Peer Conflicts with `--force` / `--legacy-peer-deps`** | High (silent runtime crash) | Medium | Resolve root conflict instead! |

## 7. Real Production Scenario
A team ran `npx npm-check-updates -u && npm install --legacy-peer-deps` across 34 packages to patch 1 security CVE. Local Windows dev started fine, yet production Alpine Docker builds failed on `sharp` (`musl` mismatch), Tailwind v4 silently removed button pointer cursors, and a major ORM bump changed `COUNT(*)` return type from `number` to `string` breaking pagination math! Reverting, isolating the single CVE fix first, then executing 4 incremental grouped upgrades with `/context7` migration guides and Docker Linux test builds completed cleanly with zero incidents.

## 8. Failure Modes & Edge Cases
- **WRONG:** Passing `--legacy-peer-deps` or `--force` blindly when `npm install` warns about incompatible peer dependencies (e.g., React 19 + a React 18-only library).
  **RIGHT:** Inspect exact `peerDependencies` via `npm view`, upgrade or replace incompatible dependents cleanly, or hold the major bump until compatible versions exist.
- **WRONG:** Upgrading a package without regenerating and committing the exact lockfile (`package-lock.json`/`uv.lock`/`go.sum`) and verifying SBOM parity (`/shadow-supplychain`).
  **RIGHT:** Always update lockfiles deterministically via the package manager and re-run supply-chain verification.

## 9. Testing & Verification
- Verify clean install (`npm ci` / `uv sync --frozen`), strict typecheck (`tsc --noEmit`), full test suite (`/shadow-test`), AND target Linux Docker image build before merging any major upgrade.

## 10. Operational Considerations
- Pair security-driven dependency upgrades with `/shadow-supplychain` reachability triage so critical runtime CVEs patch immediately while non-reachable major refactors schedule calmly.

## 11. Authoritative References
- Semantic Versioning 2.0.0 & npm `engines`/`peerDependencies` Specification.
- `shadow-monarch/reference/OFFICIAL-FIRST-DEPENDENCY-POLICY.md`.
- `/context7` MCP official library migration guides.

## 12. Limitations & When NOT to Use
- Do NOT perform unsolicited major framework upgrades during an unrelated bug-fix or minor feature task (`L2_SCOPE_EXPANSION`).
