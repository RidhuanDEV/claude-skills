# 01 — Semantic Versioning 2.0.0, Release Changelogs & The 8 Pre-Flight Gates

## 1. Purpose & Activation Conditions
Ensure every production release carries an unambiguous **SemVer 2.0.0** version, operator-ready **CHANGELOG**, immutable artifact digest, and **100% hard-gated pass across all 8 Pre-Flight Release Gates** (treating any missing prerequisite as `BLOCKED`, never "warn and ship"). Activate whenever preparing a staging promotion, tagging a release, or running a Go/No-Go release readiness audit.

## 2. Prerequisites
- Exact candidate Git commit SHA (`git rev-parse HEAD`), previous deployed immutable tag/digest (`PREV_TAG`), and commit log since `PREV_TAG`.
- Evidence outputs from `/shadow-test`, `/shadow-quality`, `/shadow-sec`, `/shadow-uat`, `/shadow-supplychain`, and (for stateful deploys) `/shadow-resilience` & `/shadow-data`.

## 3. Technical Principles & Constraints
- **SemVer 2.0.0 Contract (`MAJOR.MINOR.PATCH`):**
  - `MAJOR` (`v2.0.0`): ANY breaking API, webhook, event schema, CLI flag, or config contract change (requires `/shadow-compat` deprecation & migration guide).
  - `MINOR` (`v1.4.0`): Backward-compatible features, additive optional fields, Expand-Only DB columns (`feat:`).
  - `PATCH` (`v1.3.3`): Backward-compatible bug fixes, security patches, performance tuning (`fix:`, `sec:`, `perf:`).
- **8 Mandatory Pre-Flight Gates (Hard `BLOCKED` on Any Gap):**
  1. **Gate 1 — Quality & Tests:** Lint, strict typecheck, and automated test suite pass on the **exact release commit SHA** (not 3 commits ago!).
  2. **Gate 2 — Security Audit (`/shadow-sec`):** Zero hardcoded secrets, zero reachable critical/high vulnerabilities, auth/tenant boundaries verified.
  3. **Gate 3 — Pre-UAT Performance & Staging UAT:** Staging `/shadow-uat` sign-off (and `/shadow-perf` baseline where applicable) passed.
  4. **Gate 4 — Pre-Deploy Recovery Point:** For stateful migrations, verified recent backup + tested restore path (`/shadow-resilience`); for static sites/libraries, verified previous immutable asset/package version.
  5. **Gate 5 — Migration-Before-Code (`Expand-Only`):** Schema migrations run & verify cleanly BEFORE deploying new containers, with zero destructive `DROP`/`ALTER TYPE` during rolling deploy (`02`).
  6. **Gate 6 — Environment Parity:** Every new key in `.env.example` is confirmed present in target server/secret manager (never discovered by a `500` crash after deploy!).
  7. **Gate 7 — Immutable Rollback Command Ready:** Exact `PREV_TAG` / `@sha256:...` digest recorded with a tested 1-command rollback script.
  8. **Gate 8 — Supply-Chain SBOM, Provenance & Dependency Pinning (`/shadow-supplychain`):** CycloneDX/SPDX SBOM matches lockfile, zero floating `:latest` tags, SLSA provenance receipt verified, and every newly adopted package carries an 8-field Official-First Decision Record (`official_first_verifier.py`).
- **Immutable Build-Once, Promote-Everywhere Rule:** Promote the **exact same built OCI digest** (`ghcr.io/org/api@sha256:...`) verified in Staging into Production — never run a fresh `npm install && docker build` separately for Production!

## 4. Architecture & Implementation

### Standard Operator-Ready `CHANGELOG.md` Release Section
```markdown
## [v1.4.0] - 2026-11-22 (`sha: 9f2a1c4`)
- **Artifact Digest:** `ghcr.io/org/checkout-api@sha256:abc123...`
- **Previous Rollback Target:** `v1.3.2` (`ghcr.io/org/checkout-api@sha256:999888...`)

### Breaking Changes & Required Operator Action
- None (fully backward-compatible with `v1.3.2` N-1 pods).
- New optional env var: `CHECKOUT_CANARY_PCT` (default `0`).

### Added
- Deterministic tenant canary cohort routing for new invoice PDF renderer (`#412`).

### Fixed
- Prevent duplicate webhook dispatch on Redis ack timeout (`#408`).

### Security & Supply-Chain
- SBOM CycloneDX verified (`0` lockfile drift); all GitHub Actions pinned to 40-char SHA.

### 1-Command Rollback Procedure (Authorized L4 Only)
- `PREV_IMAGE="ghcr.io/org/checkout-api@sha256:999888..." docker compose -f docker-compose.prod.yml up -d --no-build api`
```

### 8-Gate Pre-Flight Verification Matrix

| Gate | Owner Skill | Artifact Required | Failure Action |
| :--- | :--- | :--- | :--- |
| **1. Quality & Tests** | `/shadow-test`, `/shadow-quality` | CI green run URL + exact commit SHA | `BLOCKED` |
| **2. Security** | `/shadow-sec` | ASVS/secret scan report (`0` reachable criticals) | `BLOCKED` |
| **3. UAT & Perf** | `/shadow-uat`, `/shadow-perf` | Staging sign-off / perf budget receipt | `BLOCKED` |
| **4. Backup / Recovery** | `/shadow-resilience` | Verified backup snapshot ID / previous package pin | `BLOCKED` |
| **5. Migration Safety** | `/shadow-data`, `/shadow-db` | Expand-Only SQL plan (`before_code`) | `BLOCKED` |
| **6. Env Parity** | `/shadow-ops` | Diff of `.env.example` vs target secret keys (redacted!) | `BLOCKED` |
| **7. Rollback Target** | `/shadow-release` | Pinned `PREV_TAG` digest + verified command | `BLOCKED` |
| **8. SBOM & Provenance** | `/shadow-supplychain` | `supplychain_sbom_gate.py` `VERIFIED_RECEIPT` | `BLOCKED` |

## 5. Platform/Vendor Variations
- **Libraries & SDKs (npm / PyPI / Crates / Go Modules):** Gate 4 is the immutable previous published version + deprecation notice policy; verify clean build tarball contents (`npm pack --dry-run`) so `.env` or test fixtures never publish to a public registry!
- **Static Sites / Edge Functions (Cloudflare Pages / Vercel / Netlify):** Each deployment gets an immutable deployment ID — record the exact previous deployment URL/ID for instant 1-click alias rollback.
- **Mobile Apps (App Store / Play Store):** You CANNOT roll back an already-installed binary on users' phones! Pair releases with staged rollout (`1% -> 5% -> 20% -> 100%`), server-side feature kill-switches (`03`), and `/shadow-mobile` store gates.

## 6. Decision Matrix & Trade-Offs

| Release Cadence | Batch Size | Rollback Simplicity | Operational Overhead |
| :--- | :--- | :--- | :--- |
| **Small Frequent Releases (Daily/Weekly)** | Tiny (1–5 PRs) | **Trivial** (tiny blast radius) | Low once CI gates are automated |
| **Giant Quarterly Mega-Release (200 PRs)** | Huge | **Painful** (coupled DB/API/UI changes) | High incident & war-room cost |

## 7. Real Production Scenario
A team deployed `v2.3.0` using `:latest` Docker tags without checking `.env.example` parity. Startup crashed immediately because a newly added `WEBHOOK_SIGNING_KEY` was missing in production secrets, AND attempting to roll back failed because the previous `:latest` tag had just been overwritten in the registry! Adopting immutable `@sha256:` digest promotion, `.env` key-presence diff checks (Gate 6), and running `release_readiness_verifier.py` in CI eliminated un-rollbackable deploys completely.

## 8. Failure Modes & Edge Cases
- **WRONG:** Shipping a release with `"Gate 8 SBOM: TODO next sprint"` or building a fresh Docker image on the production VPS instead of promoting the Staging-tested digest.
  **RIGHT:** Treat every missing required gate artifact as `BLOCKED` and promote the exact Staging-verified digest.
- **WRONG:** Running tests on commit `abc111`, then pushing a "tiny 1-line comment/config tweak" `abc222` and deploying `abc222` without re-running Gate 1.
  **RIGHT:** Gate 1 MUST prove green execution on the **exact release commit SHA** being deployed.

## 9. Testing & Verification
- Run `python shadow-release/scripts/release_readiness_verifier.py --check-release path/to/release_manifest.json` before proposing any production deploy.
- Run `python shadow-release/scripts/release_readiness_verifier.py --self-test` and `python -m unittest discover -s shadow-release/tests -v`.

## 10. Operational Considerations
- Keep release checklists stored in PR/release descriptions (`docs/releases/vX.Y.Z.md`) for audit traceability (`/shadow-grc`, `/shadow-pmo`).

## 11. Authoritative References
- Semantic Versioning 2.0.0 Specification (semver.org).
- Keep a Changelog 1.1.0 Specification (keepachangelog.com).
- NIST SP 800-218 (SSDF) — *PW.6 & RV.1 Release Verification*.

## 12. Limitations & When NOT to Use
- Preparing release manifests, SemVer notes, and running `release_readiness_verifier.py` is `L0_READ_ONLY` — it NEVER grants permission to execute live deploys, tag pushes, or prod DB migrations (`04`).
