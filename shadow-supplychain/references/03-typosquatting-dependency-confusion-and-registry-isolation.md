# 03 — Typosquatting, Dependency Confusion, Pre-Adoption Inspection & Registry Isolation

## 1. Purpose & Activation Conditions
Stop supply-chain compromises **before malicious code ever executes on a developer machine or CI runner** by defending against **typosquatting / slopsquatting**, **private-package dependency confusion**, **malicious `postinstall` hooks**, and **accidental replacement of trusted local internal SDKs**. Activate whenever adopting a new third-party library, configuring private registries (`.npmrc`, `pip.conf`, `GOPRIVATE`), or auditing suspicious dependencies.

## 2. Prerequisites
- Access to package registry read-only metadata commands (`npm view`, `pip index`, PyPI/crates JSON API, `/context7`) and `shadow-monarch/scripts/official_first_verifier.py`.

## 3. Technical Principles & Constraints
- **NEVER Install an Unverified Package Merely to Inspect It (`OFFICIAL-FIRST-DEPENDENCY-POLICY.md` Phase 3):**
  - Running `npm install <pkg>` or `pip install <pkg>` **immediately executes arbitrary attacker code** inside `preinstall`/`postinstall` or `setup.py`!
  - ALWAYS run **non-destructive metadata inspection** FIRST:
    - `npm view <pkg> version repository maintainers engines dist-tags license time.created --json`
    - Check: official repository link matches GitHub org, active recognized maintainers, publish age (`< 30` days on a lookalike name = massive red flag!), download volume, clean license, zero surprise `postinstall` binary downloads (`npm view <pkg> scripts`).
- **Slopsquatting & Typosquatting Defense:** Attackers register names commonly hallucinated by LLMs or 1 character off popular libraries (`lodahs`, `reqeusts`, `your-org-sso` mimicking local `file:../sdk/sso-client`!). Verify exact spelling against official docs (`/context7`) and **NEVER** replace local workspace/file SDKs with public registry packages!
- **Private Registry Isolation (Zero Dependency Confusion):**
  - If your company uses private package `@company/auth-core` or `company-internal-utils`, an attacker who publishes `@company/auth-core@99.99.99` on public npm/PyPI hijacks installs unless package-manager resolution is strictly scoped!
  - **Node (`.npmrc`):** Always bind private scopes explicitly (`@company:registry=https://npm.pkg.github.com/`) and NEVER use unscoped private package names!
  - **Python (`pip`/`uv`):** Never mix `--extra-index-url` with an unscoped private package name (pip compares version numbers across BOTH indexes and picks public `99.99.99`!) — route private packages through a **single proxy mirror** (Artifactory / Nexus / AWS CodeArtifact) or `uv` explicit per-package `[[tool.uv.index]]` pinning!
  - **Go (`GOPRIVATE`):** Set `GOPRIVATE=github.com/company/*` so private module paths never leak to public `proxy.golang.org` or `sum.golang.org`!
- **Private Artifact Mirror / Checksum Resilience:** Cache verified artifacts in a private mirror with lockfile SHA-512 integrity hashes so an upstream maintainer unpublishing a package ("left-pad" attack) cannot break emergency production security rebuilds.

## 4. Architecture & Implementation

### Non-Destructive Pre-Adoption Inspection Checklist (`L0_READ_ONLY`)
```powershell
# 1. Inspect npm metadata WITHOUT installing or executing postinstall scripts!
npm view zod version repository maintainers engines license scripts dist-tags --json

# 2. Verify 8-field Official-First Decision Record before adopting
python "shadow-monarch/scripts/official_first_verifier.py" --self-test
```

### Registry Isolation Configuration Templates
```ini
# .npmrc — Scoped Private Registry Isolation + Integrity Enforcement
@company:registry=https://npm.pkg.github.com/
//npm.pkg.github.com/:_authToken=${NODE_AUTH_TOKEN}
ignore-scripts=true
save-exact=true
```

```toml
# pyproject.toml (uv) — Explicit Source Pinning (Eliminates --extra-index-url Confusion!)
[[tool.uv.index]]
name = "company-private"
url = "https://pkgs.company.internal/simple/"
explicit = true

[tool.uv.sources]
company-auth-sdk = { index = "company-private" }
```

### Dependency Risk & Anti-Confusion Matrix

| Threat Vector | How Attack Succeeds | Deterministic Defense |
| :--- | :--- | :--- |
| **Typosquatting / Slopsquatting** | Installing lookalike or hallucinated pkg name | Verify exact name via `/context7` + `npm view` maintainers/repo BEFORE install |
| **Local SDK Substitution** | Replacing `file:../sdk/sso-client` with lookalike public pkg | Preserve local workspace/file SDK strictly; block public lookalikes |
| **npm Dependency Confusion** | Unscoped private name outranked by public `99.0.0` | Mandatory `@org/` scope + `@org:registry=...` in committed `.npmrc` |
| **Python `--extra-index-url` Confusion** | Public PyPI `99.0.0` beats private `1.2.0` | Single corporate proxy index OR `uv` `explicit = true` per-package index |
| **Malicious `postinstall` Hook** | Arbitrary shell execution during `npm install` | `ignore-scripts=true` default; allowlist audited native builds explicitly |

## 5. Platform/Vendor Variations
- **pnpm v10+ (`onlyBuiltDependencies`):** pnpm v10 blocks dependency lifecycle build scripts by default unless explicitly allowlisted in `package.json` (`pnpm.onlyBuiltDependencies`) — a huge defense-in-depth win!
- **Socket.dev / OSV-Scanner / GuardDog:** Static behavioral scanners inspect newly added packages for obfuscated `eval`, `child_process`, reading `~/.ssh`/`process.env`, or outbound DNS beacons inside install hooks before PR merge.

## 6. Decision Matrix & Trade-Offs

| Adoption Control | Developer Friction | Security Value | Required For |
| :--- | :---: | :---: | :--- |
| **`npm view` + 8-Field Decision Record** | `< 30 seconds` | **Very High** | Every new dependency addition |
| **Scoped `.npmrc` / `uv` Explicit Index / `GOPRIVATE`** | One-time setup | **Critical** | Any org with internal packages |
| **`ignore-scripts=true` + Explicit Build Allowlist** | Very Low | **High** | All CI & developer workstations |

## 7. Real Production Scenario
During a refactor, an automated assistant saw `import { verifySso } from 'your-org-sso'` (backed by `"your-org-sso": "file:../sdk/sso-client"`), assumed it was a broken public dependency, and attempted to run `npm install your-org-sso` from public npm. Enforcing Phase 3 non-destructive inspection + local SDK preservation caught the substitution before execution, preserved the trusted `file:../sdk/sso-client` contract, and locked `.npmrc` with `ignore-scripts=true`.

## 8. Failure Modes & Edge Cases
- **WRONG:** Passing `--extra-index-url https://private.corp/simple` in `pip install` alongside default PyPI for an internal package `corp-billing` (classic Alex Birsan dependency confusion RCE!).
  **RIGHT:** Use a single internal proxy repository that blocks upstream fallback for private namespaces, or `uv` `explicit = true` per-package index routing.
- **WRONG:** Committing a plaintext personal access token inside `.npmrc` (`_authToken=ghp_1234...`).
  **RIGHT:** Reference an environment variable (`${NODE_AUTH_TOKEN}`) injected strictly at CI/dev runtime (`shadow-sec`).

## 9. Testing & Verification
- Verify `.npmrc` / `pyproject.toml` / `go env GOPRIVATE` contain zero hardcoded tokens and strictly scope every internal package namespace.
- Verify `python shadow-monarch/scripts/official_first_verifier.py --self-test` passes cleanly.

## 10. Operational Considerations
- Maintain a pinned internal registry mirror (Verdaccio / Nexus / Artifactory / Artifact Registry) for regulated enterprise systems so public npm/PyPI outages or unpublishes never halt emergency hotfix builds.

## 11. Authoritative References
- Alex Birsan — *Dependency Confusion: How I Hacked Into Apple, Microsoft and Dozens of Other Companies*.
- OpenSSF — *Concise Guide for Evaluating Open Source Software*.
- `shadow-monarch/reference/OFFICIAL-FIRST-DEPENDENCY-POLICY.md`.

## 12. Limitations & When NOT to Use
- Registry scoping defends against external hijacking, NOT against a compromised maintainer of an already-trusted popular package — combine with 40-char SHA/lockfile pinning (`02`), SBOM reconciliation (`01`), and SLSA provenance (`04`).
