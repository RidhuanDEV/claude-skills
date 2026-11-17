---
name: shadow-supplychain
description: "Dependency, Build & Artifact Supply-Chain Integrity. Use when generating or verifying CycloneDX/SPDX SBOMs against resolved lockfiles, detecting typosquatting/dependency confusion, auditing transitive dependency reachability, enforcing pinned CI/container digests, checking license policies, or validating SLSA provenance attestations. Do NOT use for general AppSec STRIDE/SAST (shadow-sec), server operations (shadow-ops), or SemVer changelogs (shadow-release)."
---

# `/shadow-supplychain` — Dependency, Build & Artifact Integrity

- **Owner:** SBOM vs lockfile integrity, transitive reachability, dependency confusion/typosquatting defense, pinned build inputs, SLSA provenance, license policy, and time-bounded security waivers.
- **Boundaries:** AppSec STRIDE/SAST/ASVS (`shadow-sec`), server/K8s operations (`shadow-ops`), SemVer rollout/rollback (`shadow-release`).

## 1. Preconditions, Isolation & Failure Rules
- **Offline/Restricted Environments:** Explicitly declare when vulnerability databases or external signature registries are unreachable (`UNVERIFIED` / `NOT_RUN`), never fabricating provenance trust.
- **Zero Unverifiable Trust:** Reject artifacts with unverifiable signer identity, floating mutable image/action tags (`:latest`, `@main`), or SBOMs diverging from resolved lockfiles.
- **Pre-Adoption Registry Inspection (`OFFICIAL-FIRST-DEPENDENCY-POLICY.md` Phase 3):** Before installing any new package, run non-destructive metadata inspection (`npm view <pkg> version repository maintainers engines dist-tags`), verify publisher authenticity, provenance, license, and advisories, pin approved versions in regulated/prod envs, and NEVER install an unverified package merely to inspect it.

## 2. 6-Step Supply-Chain Integrity Playbook
Read [`methodologies/SBOM-SLSA-PROVENANCE-AND-LOCKFILE-INTEGRITY.md`](methodologies/SBOM-SLSA-PROVENANCE-AND-LOCKFILE-INTEGRITY.md) and [`playbooks/SBOM-RISK-REGISTER-AND-ATTESTATION.md`](playbooks/SBOM-RISK-REGISTER-AND-ATTESTATION.md):
1. **Inventory Build Chain & Lockfiles:** Verify `package-lock.json`, `pnpm-lock.yaml`, `poetry.lock`, `go.sum`, `Cargo.lock`, CI workflows, and base container images.
2. **Validate Origin & Anti-Confusion Controls:** Detect lookalike typosquatted packages, scoped private registry mismatches, and unpinned GitHub Actions (`uses: org/action@v1` -> must pin 40-char SHA).
3. **Generate & Reconcile SBOM (CycloneDX / SPDX):** Cross-check emitted SBOM components 1:1 against resolved lockfile dependencies (`0` phantom/missing packages).
4. **Prioritize by Reachability & Fix Availability:** Triage CVEs by production runtime reachability rather than noisy dev-only alerts; enforce expiry dates on waivers.
5. **Enforce Isolated Reproducible Build & Provenance:** Build in isolated CI runners without leaking secrets; sign artifacts and emit SLSA provenance attestations where supported.
6. **Verify Before Release Handoff:** Hand verified SBOM + provenance digest to `/shadow-release` and `/shadow-handover`.

```powershell
python "shadow-supplychain/scripts/supplychain_sbom_gate.py" --self-test
python "shadow-supplychain/scripts/supplychain_sbom_gate.py" --verify path/to/supplychain_manifest.json
```
