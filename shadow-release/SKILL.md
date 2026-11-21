---
name: shadow-release
description: "Production Release & Rollback Management. Use when preparing production deployments, SemVer changelogs, pre-flight checklists, migration backward-compatibility gates, feature flags, or rollback runbooks."
---

# Shadow Release (`/shadow-release`) — Release Readiness Gate, Versioning & Rollback Verification

Use this skill before every Staging or Production deployment to guarantee that a release is traceable, backward-compatible, backed up, and instantly reversible if an incident occurs.

---

## 1. Semantic Versioning & Release Manifest (`SemVer 2.0.0`)

Determine version bump (`MAJOR.MINOR.PATCH`) from the verified commit history since the last tag:
- **`MAJOR` (`v2.0.0`)**: Breaking API/webhook contract changes or incompatible architecture shifts (requires `/shadow-compat` migration plan).
- **`MINOR` (`v1.3.0`)**: Backward-compatible new features, endpoints, or additive DB migrations (`feat:`).
- **`PATCH` (`v1.2.1`)**: Backward-compatible bug fixes, security patches, or performance tuning (`fix:`, `perf:`, `sec:`).

### Release Notes / `CHANGELOG.md` Structure
Group all user- and operator-relevant changes under:
1. **Breaking Changes & Required Action (`ENV` vars, migrations, config updates)**
2. **Added (`Features`)**
3. **Fixed (`Bug Fixes`)**
4. **Security & Performance**
5. **Rollback Instructions (Exact git tag / image digest & command)**

---

## 2. Pre-Flight Release Readiness Checklist (Gate 6)

> [!CAUTION]
> **Read-Only Default Rule**: `/shadow-release` prepares and audits the release checklist first. Never execute a live production deployment or production DB migration without explicit confirmation from the **Monarch**.

Before deploying to Production, verify all 8 release gates (treat any missing required artifact as an immediate `BLOCKED` status — never "warn and ship"):
- [ ] **Gate 1 — Quality & Tests**: Lint, strict typecheck, and automated test suite (`/shadow-test` + `/shadow-quality`) pass on the exact release commit SHA.
- [ ] **Gate 2 — Security Audit**: `/shadow-sec` reports zero hardcoded secrets, zero reachable critical vulnerabilities, and auth/tenant guards verified.
- [ ] **Gate 3 — Pre-UAT Performance & Staging UAT**: `/shadow-perf` baseline and `/shadow-uat` Staging verification passed.
- [ ] **Gate 4 — Pre-Deploy Database Backup**: For a stateful migration, verify an authorized recovery point and tested restore path. For a static site or library, verify recovery of its previous asset/package version.
- [ ] **Gate 5 — Migration-Before-Code Ordering (`/shadow-data`)**: Expand-only migrations execute and verify cleanly **before** deploying new application containers so rolling back code remains safe; defer destructive Contract/cleanup migrations until old instances finish draining.
- [ ] **Gate 6 — Environment Parity**: Any new `.env` keys added in `.env.example` are confirmed present in the target server/secret manager.
- [ ] **Gate 7 — Rollback Command Ready**: Previous working image tag / commit SHA recorded (`PREV_TAG`) with a 1-command rollback script tested.
- [ ] **Gate 8 — Supply-Chain SBOM & Provenance (`/shadow-supplychain`)**: Verify generated CycloneDX/SPDX SBOM, lockfile integrity, immutable container image digest pinning (zero `:latest` / floating action tags), and build provenance attestation (`supplychain_sbom_gate.py`). Missing SBOM or provenance artifact blocks release (`BLOCKED`).

---

## 3. Post-Deploy Production Smoke Verification

Immediately after deployment finishes (within `< 2 minutes`):
1. Discover the deployed readiness signal and one representative consumer journey. Compare canary and control by client version and traffic mix; hold on missing coverage or incompatible reader/writer skew.
2. Check container/service logs (`docker compose logs --tail=50` / `journalctl`) for zero startup errors.
3. Execute read-only smoke checks on critical public/authenticated routes (`/shadow-api` / `/shadow-browser`).
4. Compare the candidate against a healthy cohort or the agreed service baseline. Use the release-specific observation window, minimum traffic and abort threshold. On breach, halt promotion and confirm the previous artifact can consume current data and configuration before invoking an authorized rollback. For incompatible migrations contain writes or roll forward with the incident owner.
5. **Execution Approval Boundary (`L0` vs `L4`)**: Preparing release checklists, SBOM verification, and SemVer changelogs is `L0_READ_ONLY`. Executing production deploys, live migrations, or tag pushes is **`L4: HIGH_IMPACT`** requiring explicit 7-part Monarch approval and rollback verification (`shadow-monarch/scripts/execution_approval_gate.py`).
6. **Dependency Traceability & Pinning (`OFFICIAL-FIRST-DEPENDENCY-POLICY.md`)**: Confirm every newly adopted package in the release has a `Verified` 8-field Decision Record, pinned version (no floating `latest`), and lockfile parity (`official_first_verifier.py`).

## Reference Guide

| Task / Scenario | Load Reference |
| :--- | :--- |
| Kill-Switch Flags, Deterministic Canary Cohorts, `< 2 Min` Smoke Probes & Safe Rollback vs Forward-Fix | [references/release-and-rollback-execution.md](references/release-and-rollback-execution.md) |

Do not load unrelated references unnecessarily.
