---
name: shadow-release
description: "Use when planning SemVer, release preflight, canaries, feature flags, smoke checks, or rollback. Not for provisioning (/shadow-ops)."
---

# Shadow Release (`/shadow-release`) — Release Readiness Gates, Versioning & Rollback Verification

Use this skill before every Staging or Production deployment to guarantee that a release is traceable, SemVer-accurate, backward-compatible (`N` / `N-1` skew-safe), backed up, supply-chain verified, and instantly reversible if an incident occurs.

- **Owner:** SemVer 2.0.0 & `CHANGELOG.md`, 8 hard Pre-Flight Release Gates (`release_readiness_verifier.py`), Expand-Only migration-before-code ordering, deterministic canary cohorts & kill-switch flags, `< 2 min` post-deploy smoke verification, rollback vs forward-fix decision trees, and `L0` vs `L4` release change governance.
- **Boundaries:** Server/Docker/K8s/Nginx provisioning (`shadow-ops`), SBOM/SLSA signing & verification (`shadow-supplychain`), API deprecation/compatibility design (`shadow-compat`), DB backfill execution (`shadow-data`), and post-incident SLA/postmortems (`shadow-maintain`).

## Reference Guide

Load ONLY the 1–2 modular playbooks needed for the active release subtask:

| Module | Topic | Load When |
| :--- | :--- | :--- |
| [01-semver-changelogs-and-8-gate-preflight.md](references/01-semver-changelogs-and-8-gate-preflight.md) | SemVer 2.0.0 rules, operator-ready `CHANGELOG.md`, 8 mandatory Pre-Flight Gates (hard `BLOCKED`), immutable digest promotion | Preparing release notes, running Go/No-Go pre-flight readiness audits |
| [02-migration-before-code-and-skew-safety.md](references/02-migration-before-code-and-skew-safety.md) | `N`/`N-1` rolling skew law, 3-release Expand-Contract, dedicated pre-deploy migration jobs, versioned Redis `:v2:` & queue consumers | Planning releases containing SQL DDL, Redis schema, or async queue changes |
| [03-feature-flags-canaries-and-smoke-probes.md](references/03-feature-flags-canaries-and-smoke-probes.md) | Deterministic SHA-256 canary bucketing (never `Math.random`), instant kill-switch flags, abort thresholds, `< 2 min` `/readyz` SHA smoke check | Launching high-risk features progressively or writing post-deploy smoke probes |
| [04-rollback-vs-forward-fix-and-l4-governance.md](references/04-rollback-vs-forward-fix-and-l4-governance.md) | `N-1` compatibility check before rollback, write containment + forward-fix on destructive DDL, tested 1-command rollbacks, `L0` vs `L4` gate | Executing post-deploy incident triage, rollback runbooks, or `L4` release authorization |
| [evaluations.md](evaluations.md) | Graded specialist evaluation scenarios (`REL-EVAL-01..07`) | Auditing gate enforcement, SemVer integrity, migration ordering, canary rigor, and `L4` bounds |

---

## 1. The 8 Pre-Flight Release Readiness Gates (Hard `BLOCKED` on Any Gap)

> [!CAUTION]
> **Read-Only Default (`L0` vs `L4`):** Preparing checklists, SemVer changelogs, SBOM checks, and running `release_readiness_verifier.py` is **`L0_READ_ONLY`**. Executing production deploys, live migrations, or `git push --tags` is **`L4_HIGH_IMPACT`** requiring explicit 7-part Monarch approval (`shadow-monarch/scripts/execution_approval_gate.py`).

Treat any missing required artifact as **`BLOCKED`** — never "warn and ship":
1. **Gate 1 — Quality & Tests:** Lint, strict typecheck, and automated test suite (`/shadow-test` + `/shadow-quality`) pass on the **exact release commit SHA**.
2. **Gate 2 — Security Audit:** `/shadow-sec` reports zero hardcoded secrets, zero reachable criticals, and auth/tenant guards verified.
3. **Gate 3 — Pre-UAT Performance & Staging UAT:** `/shadow-perf` baseline and `/shadow-uat` Staging verification passed.
4. **Gate 4 — Pre-Deploy Recovery Point:** Verified authorized backup + tested restore path (`/shadow-resilience`) for stateful services, or verified previous immutable version for static sites/libraries.
5. **Gate 5 — Expand-Only Migration-Before-Code (`/shadow-data`):** Expand-Only migrations execute **before** deploying new containers so `N-1` rollback stays safe; defer destructive `DROP` Contract DDL until old instances finish draining.
6. **Gate 6 — Environment Parity:** Every new key in `.env.example` is confirmed present in target server/secret manager.
7. **Gate 7 — Immutable Rollback Target Ready:** Previous working immutable tag/digest (`PREV_TAG`, zero `:latest`) recorded with a tested 1-command rollback script.
8. **Gate 8 — Supply-Chain SBOM, Provenance & Pinning (`/shadow-supplychain`):** CycloneDX/SPDX SBOM matches lockfile, pinned digests/versions (8-field Official-First Decision Record), and verified SLSA provenance (`supplychain_sbom_gate.py`).

---

## 2. Post-Deploy Smoke Verification & Safe Rollback Rule

Immediately after deploy (`< 2 minutes`):
1. Verify `/readyz` returns healthy AND exact deployed `releaseSha === ExpectedSha`, inspect startup logs (`docker compose logs --tail=50` / `journalctl`) for zero errors, and execute read-only smoke probes.
2. Compare canary vs matched healthy control cohort over the pre-agreed minimum window and sample size. On abort-threshold breach: capture redacted evidence first, flip kill-switch (`< 5s`) if flagged, or confirm `N-1` data/config compatibility BEFORE invoking an authorized `PREV_TAG` rollback. If destructive DDL already mutated production data, contain writes and roll forward with the incident owner!

---

## 3. Deterministic Release Readiness Verification

```powershell
python shadow-release/scripts/release_readiness_verifier.py --self-test
python shadow-release/scripts/release_readiness_verifier.py --check-release path/to/release_manifest.json
python -m unittest discover -s shadow-release/tests -v
```
