---
name: shadow-release
description: Production Release Management: Semantic Versioning, Release Notes / Changelog generation, Pre-Flight Deployment Checklist, Database Migration Backward-Compatibility Gate, Feature Flags, Post-Deploy Smoke Verification, and Verified Rollback Runbook. Trigger with /shadow-release.
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

Before deploying to Production, verify all 7 gates:
- [ ] **Gate 1 — Quality & Tests**: Lint, strict typecheck, and automated test suite (`/shadow-test` + `/shadow-quality`) pass on the exact release commit SHA.
- [ ] **Gate 2 — Security Audit**: `/shadow-sec` reports zero hardcoded secrets, zero critical vulnerabilities, and auth/tenant guards verified.
- [ ] **Gate 3 — Pre-UAT Performance & Staging UAT**: `/shadow-perf` baseline and `/shadow-uat` Staging verification passed.
- [ ] **Gate 4 — Pre-Deploy Database Backup**: Fresh production database backup (`pg_dump` / `mysqldump`) created and checksum-verified (`/shadow-ops`).
- [ ] **Gate 5 — Migration Safety (`/shadow-data`)**: All pending SQL migrations are expand-only / backward-compatible with the currently running application version so rolling back the container will not crash against the migrated schema.
- [ ] **Gate 6 — Environment Parity**: Any new `.env` keys added in `.env.example` are confirmed present in the target server/secret manager.
- [ ] **Gate 7 — Rollback Command Ready**: Previous working image tag / commit SHA recorded (`PREV_TAG`) with a 1-command rollback script tested.

---

## 3. Post-Deploy Production Smoke Verification

Immediately after deployment finishes (within `< 2 minutes`):
1. Check `/healthz` and `/readyz` return `200 OK`.
2. Check container/service logs (`docker compose logs --tail=50` / `journalctl`) for zero startup errors.
3. Execute read-only smoke checks on critical public/authenticated routes (`/shadow-api` / `/shadow-browser`).
4. Monitor error rate and `p95` latency for 15 minutes (`/shadow-observe`). If 5xx rate spikes above threshold, execute the rollback command immediately.
