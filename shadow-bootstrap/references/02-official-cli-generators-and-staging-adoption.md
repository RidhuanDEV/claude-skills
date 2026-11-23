# 02 — Official CLI Generators, Sibling Staging Adoption & Dependency Verification

## 1. Purpose & Activation Conditions
Execute **verified official CLI project generators** (`npm create vite`, `create-next-app`, `@nestjs/cli`, `uv init`, `cargo init`, `go mod init`, `composer create-project`) safely — inspecting package identity, exact versions, and side effects BEFORE running, and isolating risky generators inside a **sibling staging directory** before adopting diffs. Activate whenever bootstrapping any new framework/language project.

## 2. Prerequisites
- Passed `preview_scaffold.py` target check (`01`) and confirmed stack/profile choice.
- Access to `/context7` MCP or non-destructive package registry lookup (`npm view`, `official_first_verifier.py`).

## 3. Technical Principles & Constraints
- **Official Generator First (Never Hand-Craft Framework Boilerplate!):** Framework configs (`next.config.ts`, `vite.config.ts`, `tsconfig.json`, `eslint.config.mjs`, `composer.json`, `pyproject.toml`) evolve every minor release. Running the official CLI generator guarantees version-accurate templates AND conserves context/output tokens!
- **Pre-Invocation Generator Audit:** Before executing a generator command, record:
  1. Exact verified package/binary identity & version (check official docs via `/context7` or `npm view <generator> version repository maintainers` — guard against typosquatted generators!).
  2. Exact non-interactive CLI flags (`--ts`, `--tailwind`, `--yes`, `--no-install` where available so you control install side effects!).
  3. Exact package manager (`pnpm`/`npm`/`uv`/`composer`) and expected output files.
  4. 8-field **Official-First Decision Record** validated by `shadow-monarch/scripts/official_first_verifier.py` for core runtime dependencies.
- **Sibling Staging Directory Isolation:** Whenever a CLI generator might overwrite existing workspace files, drop an unwanted `.git` folder, or auto-install conflicting lockfiles, run the generator inside a temporary **sibling staging directory** (`../.scaffold-stage-<name>`), inspect the generated tree and `diff`, remove any nested `.git`, adopt ONLY the intended files cleanly into the target, and clean up the staging directory in `finally`!
- **Strict TypeScript / Compiler Hygiene Immediately After Generation:** Official generators sometimes emit relaxed defaults (`strict: false`, unchecked indexed access, or `console.log` sample routes). Immediately tighten compiler strictness (`"strict": true`, `"noUncheckedIndexedAccess": true`, `"forceConsistentCasingInFileNames": true`) and strip placeholder demo bloat before writing the vertical slice!

## 4. Architecture & Implementation

### Verified Official CLI Generator Command Matrix

| Ecosystem | Official Generator Command (Non-Interactive Flags) | Post-Generate Hardening Step |
| :--- | :--- | :--- |
| **Vite + React/Vue/Svelte TS** | `npm create vite@latest <dir> -- --template react-ts` | Enable `noUncheckedIndexedAccess`, restore Tailwind v4 `cursor: pointer`, clean template demo files |
| **Next.js App Router** | `npx create-next-app@latest <dir> --ts --eslint --app --src-dir --no-import-alias` | Verify `strict: true`, remove boilerplate hero assets, wire clean `/api/health` if needed |
| **NestJS / Fastify** | `npx @nestjs/cli new <dir> --strict --package-manager pnpm --skip-git` | Replace default `console.log` with `pino` JSON logger + `X-Request-Id` (`03`) |
| **Python (`uv` — Modern Standard)** | `uv init <dir>` (app) or `uv init --lib <dir>` (library) | Configure `ruff`, `mypy --strict`, `pytest`, `structlog` (`03`), frozen `uv.lock` |
| **Go** | `go mod init <module-path>` | Standard `cmd/<app>/main.go` + `internal/`, `log/slog` JSON handler, `go test -race ./...` |
| **PHP / Laravel** | `composer create-project laravel/laravel <dir>` | Configure Monolog `JsonFormatter`, `RefreshDatabase` Pest/PHPUnit tests, strict types |
| **Rust** | `cargo init <dir>` or `cargo init --lib <dir>` | Enable `#![deny(unsafe_code)]` (where applicable), `clippy`, `tracing` JSON subscriber |

### Sibling Staging Adoption Pattern (PowerShell Safe)
```powershell
$ErrorActionPreference = "Stop"
$StageDir = Join-Path (Split-Path $TargetDir -Parent) ".scaffold-stage-$PID"
try {
    npm create vite@latest $StageDir -- --template react-ts
    if ($LASTEXITCODE -ne 0) { throw "Official generator failed" }

    # Remove any nested .git generated inside staging, inspect tree, then copy cleanly
    $NestedGit = Join-Path $StageDir ".git"
    if (Test-Path $NestedGit) { Remove-Item -Recurse -Force $NestedGit }

    # Inspect diff / file list before adopting into $TargetDir
    Get-ChildItem -Path $StageDir -Recurse -Name
} finally {
    if (Test-Path $StageDir) { Remove-Item -Recurse -Force $StageDir }
}
```

## 5. Platform/Vendor Variations
- **Windows `npx` / PowerShell Quirks:** On Windows PowerShell, invoke `npx.cmd` or `npm.cmd` if child-process wrappers don't resolve `.cmd` shims, and always check `$LASTEXITCODE` after native CLI commands.
- **Offline / Restricted CI Sandboxes:** If registry network access is unavailable, report `BLOCKED` / offline clearly and fall back to verified local workspace templates or cached generators rather than inventing unverified package versions!

## 6. Decision Matrix & Trade-Offs

| Approach | Token & Maintenance Cost | Version Accuracy | Safety Inside Existing Repo |
| :--- | :--- | :--- | :--- |
| **Direct Generator into Empty Dir** | Lowest | **100%** | Safe ONLY after `preview_scaffold.py` confirms empty |
| **Sibling Staging -> Inspect Diff -> Adopt** | Low | **100%** | **Safest** for monorepos & retries |
| **Manual Boilerplate From Memory** | High (bloats tokens) | Frequently outdated | Prone to subtle config bugs |

## 7. Real Production Scenario
A developer ran `npx create-next-app` directly inside an existing `pnpm` monorepo folder (`apps/portal`). The generator silently initialized a nested `.git` repository, created a stray `package-lock.json` that broke CI `pnpm install --frozen-lockfile`, and installed `npm` packages conflicting with workspace peer dependencies. Using the Sibling Staging Adoption pattern (`--skip-git --use-pnpm`), inspecting the file diff before moving into `apps/portal`, and verifying `pnpm install --frozen-lockfile` prevented all 3 workspace corruptions cleanly.

## 8. Failure Modes & Edge Cases
- **WRONG:** Running an unverified third-party community starter template (`npx random-guy-ultimate-saas-kit`) without inspecting maintainers, repo provenance, or dependencies.
  **RIGHT:** Use ONLY verified official framework CLI generators (checked via `/context7` / `npm view` / `official_first_verifier.py`).
- **WRONG:** Leaving a nested `.git/` directory inside a newly scaffolded subfolder of a monorepo (turns the app into a broken untracked git submodule!).
  **RIGHT:** Always pass `--skip-git` (or delete nested `.git` inside staging before adoption).

## 9. Testing & Verification
- Verify `python shadow-monarch/scripts/official_first_verifier.py --self-test` passes and document the 8-field Decision Record for newly adopted core packages.
- Verify clean install + build + lint + test pass immediately after adopting the generator output.

## 10. Operational Considerations
- Remove default generator "Hello World" logos, unused CSS animations, and `console.log("Server listening on 3000")` placeholders before committing the first vertical slice.

## 11. Authoritative References
- `shadow-monarch/reference/OFFICIAL-FIRST-DEPENDENCY-POLICY.md` & `scripts/official_first_verifier.py`.
- Official CLI Generator Docs: Vite, Next.js, NestJS, Astral `uv`, Go Modules, Cargo, Composer.

## 12. Limitations & When NOT to Use
- Never silently invoke package-manager global installs (`npm install -g ...`) or modify host system PATHs without explicit approval (`L2`/`L4`); prefer pinned ephemeral invocation (`npx --yes <pkg>@<ver>`) or project-local devDependencies.
