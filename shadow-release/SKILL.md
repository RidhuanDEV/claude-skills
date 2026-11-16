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
- [ ] **Gate 4 — Pre-Deploy Database Backup**: Fresh production database backup (`pg_dump` / `mysqldump`) created and checksum-verified (`/shadow-ops`).
- [ ] **Gate 5 — Migration-Before-Code Ordering (`/shadow-data`)**: Expand-only migrations execute and verify cleanly **before** deploying new application containers so rolling back code remains safe; defer destructive Contract/cleanup migrations until old instances finish draining.
- [ ] **Gate 6 — Environment Parity**: Any new `.env` keys added in `.env.example` are confirmed present in the target server/secret manager.
- [ ] **Gate 7 — Rollback Command Ready**: Previous working image tag / commit SHA recorded (`PREV_TAG`) with a 1-command rollback script tested.
- [ ] **Gate 8 — Supply-Chain SBOM & Provenance (`/shadow-supplychain`)**: Verify generated CycloneDX/SPDX SBOM, lockfile integrity, immutable container image digest pinning (zero `:latest` / floating action tags), and build provenance attestation (`supplychain_sbom_gate.py`). Missing SBOM or provenance artifact blocks release (`BLOCKED`).

---

## 3. Post-Deploy Production Smoke Verification

Immediately after deployment finishes (within `< 2 minutes`):
1. Check `/healthz` and `/readyz` return `200 OK`.
2. Check container/service logs (`docker compose logs --tail=50` / `journalctl`) for zero startup errors.
3. Execute read-only smoke checks on critical public/authenticated routes (`/shadow-api` / `/shadow-browser`).
4. Monitor error rate and `p95` latency for 15 minutes (`/shadow-observe`). If 5xx rate spikes above threshold, execute the rollback command immediately.
5. **Execution Approval Boundary (`L0` vs `L4`)**: Preparing release checklists, SBOM verification, and SemVer changelogs is `L0_READ_ONLY`. Executing production deploys, live migrations, or tag pushes is **`L4: HIGH_IMPACT`** requiring explicit 7-part Monarch approval and rollback verification (`shadow-monarch/scripts/execution_approval_gate.py`).
