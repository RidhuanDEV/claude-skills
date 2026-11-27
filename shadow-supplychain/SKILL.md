---
name: shadow-supplychain
description: "Use when verifying SBOM, CycloneDX/SPDX, SLSA provenance, dependency confusion, transitive packages, or pinned CI artifacts."
---

# `/shadow-supplychain` — Dependency, Build & Artifact Supply-Chain Integrity

- **Owner:** CycloneDX/SPDX SBOM vs lockfile 1:1 parity, transitive reachability triage, dependency confusion/typosquatting defense, 40-char CI SHA & OCI `@sha256:` pinning, SLSA v1.2 consumer provenance reconciliation, license policy, and expiring signed CVE waivers.
- **Boundaries:** AppSec STRIDE/SAST/ASVS code audits (`shadow-sec`), server/Docker/K8s operations (`shadow-ops`), SemVer release rollout/rollback (`shadow-release`), and client BAST packaging (`shadow-handover`).

## Reference Guide

Load ONLY the 1–2 modular playbooks needed for the active supply-chain subtask:

| Module | Topic | Load When |
| :--- | :--- | :--- |
| [01-sbom-cyclonedx-spdx-and-lockfile-parity.md](references/01-sbom-cyclonedx-spdx-and-lockfile-parity.md) | CycloneDX/SPDX from frozen lockfiles, 4-tuple `(ecosystem, name, version, scope)` parity, optional platform exclusions, reachability & license screening | Generating or reconciling SBOMs, triaging transitive CVEs, auditing licenses |
| [02-ci-40-char-sha-and-container-digest-pinning.md](references/02-ci-40-char-sha-and-container-digest-pinning.md) | 40-char GitHub Actions SHA pinning, OCI `@sha256:` base images, `permissions: {}`, `persist-credentials: false`, anti-PR-injection | Hardening CI/CD workflows and production Dockerfiles against mutable tag hijacks |
| [03-typosquatting-dependency-confusion-and-registry-isolation.md](references/03-typosquatting-dependency-confusion-and-registry-isolation.md) | Non-destructive `npm view` pre-adoption audit, local SDK preservation (`file:../sdk/...`), `.npmrc` scopes, `uv` explicit indexes, `GOPRIVATE`, `ignore-scripts` | Evaluating new dependencies or preventing private-package dependency confusion |
| [04-slsa-v12-provenance-cosign-and-expiring-waivers.md](references/04-slsa-v12-provenance-cosign-and-expiring-waivers.md) | SLSA v1.2 consumer trust model, `trusted_builds` 4-tuple policy, Cosign/`gh attestation verify`, honest `OFFLINE`/`NOT_RUN`, expiring signed waivers | Verifying artifact provenance receipts and CVE exception expiry before release |
| [methodologies/SBOM-SLSA-PROVENANCE-AND-LOCKFILE-INTEGRITY.md](methodologies/SBOM-SLSA-PROVENANCE-AND-LOCKFILE-INTEGRITY.md) | Core SBOM, SLSA & lockfile integrity methodology | Reviewing end-to-end supply-chain integrity methodology |
| [playbooks/SBOM-RISK-REGISTER-AND-ATTESTATION.md](playbooks/SBOM-RISK-REGISTER-AND-ATTESTATION.md) | SBOM risk register & attestation record template | Recording supply-chain risk dispositions and audit evidence |
| [evaluations.md](evaluations.md) | Graded specialist evaluation scenarios (`SC-EVAL-01..07`) | Auditing SHA pinning, independent receipts, offline honesty, anti-confusion, and waiver expiry |

---

## 1. Preconditions, Isolation & Pre-Adoption Rules
- **Offline/Restricted Environments:** Explicitly declare **`OFFLINE`** / **`NOT_RUN`** when vulnerability databases or signature registries are unreachable — NEVER synthesize fake `VERIFIED` provenance trust.
- **Zero Unverifiable Trust:** Reject self-asserted PR manifest claims, floating mutable tags (`:latest`, `@v4`, `@main`), or SBOMs diverging from resolved lockfiles.
- **Pre-Adoption Registry Inspection (`OFFICIAL-FIRST-DEPENDENCY-POLICY.md` Phase 3):** Before installing any new package, run non-destructive metadata inspection (`npm view <pkg> version repository maintainers engines dist-tags`), verify publisher authenticity, license, and scripts, pin approved versions in regulated/prod envs, preserve local internal SDKs, and NEVER install an unverified package merely to inspect it.

---

## 2. 6-Step Supply-Chain Integrity Playbook
Read [`methodologies/SBOM-SLSA-PROVENANCE-AND-LOCKFILE-INTEGRITY.md`](methodologies/SBOM-SLSA-PROVENANCE-AND-LOCKFILE-INTEGRITY.md) and [`playbooks/SBOM-RISK-REGISTER-AND-ATTESTATION.md`](playbooks/SBOM-RISK-REGISTER-AND-ATTESTATION.md):
1. **Inventory Build Chain & Lockfiles:** Verify `package-lock.json`, `pnpm-lock.yaml`, `uv.lock`, `poetry.lock`, `go.sum`, `Cargo.lock`, CI workflows, and base container images.
2. **Validate Origin & Anti-Confusion Controls:** Detect lookalike typosquatted packages, enforce scoped private registry pinning (`.npmrc`, `uv` explicit index, `GOPRIVATE`), and pin all GitHub Actions to 40-char SHAs + OCI `@sha256:` digests.
3. **Generate & Reconcile SBOM (CycloneDX / SPDX):** Cross-check emitted SBOM components 1:1 against resolved lockfile dependencies (`0` phantom/missing runtime packages).
4. **Prioritize by Reachability & License Policy:** Triage CVEs by production runtime reachability rather than noisy dev-only alerts; enforce expiring signed waivers.
5. **Enforce Isolated Reproducible Build & Provenance:** Build on isolated CI runners with `permissions: {}` & `persist-credentials: false`; sign artifacts and emit SLSA v1.2 provenance attestations.
6. **Verify Before Release Handoff:** Hand verified `VERIFIED_RECEIPT`, SBOM, and waiver register to `/shadow-release` (Gate 8) and `/shadow-handover`.

```powershell
python "shadow-supplychain/scripts/supplychain_sbom_gate.py" --self-test
python "shadow-supplychain/scripts/supplychain_sbom_gate.py" --verify manifest.json --policy consumer-policy.json --artifact release.bin --receipt verifier-result.json --as-of-date 2026-11-23
python -m unittest discover -s shadow-supplychain/tests -v
```

---

## 3. Artifact-Specific Release Decision (SLSA v1.2 Consumer Trust Model)

Separate the producer's inventory from the consumer's trust policy and CI verification receipt. Inspect the repository's existing signer verification step, confirm which identity checks it actually ran, and normalize only its observed output. Read the receipt from a consumer-controlled CI channel. A receipt supplied by the artifact author, an editable PR file, or a failed verifier cannot establish signer trust. Keep the original signature, upstream output, verifier version, CI run identity, and policy revision for the reviewer. This gate hashes the artifact bytes locally and reconciles evidence; cryptographic signature verification remains with that independent verifier.

- Provide an ordered CLI handoff: normalized manifest, actual release artifact, consumer policy, verifier receipt, and the evaluation date (`--as-of-date`) for any vulnerability waiver. Historical `provenance.signer_verified` in the manifest alone yields **`INCOMPLETE`**.
- In the consumer policy, `trusted_builds` is an array of allowed **tuples** of `issuer`, `builder_id`, `build_type`, and `verifier` (optional `platform`). The verifier receipt contains those four values, `status: VERIFIED`, and lowercase hex `subject_sha256` matching the local artifact hash. For offline/unavailable checks, record `OFFLINE` or `NOT_RUN`; never synthesize a passing receipt. Verified dimension is labeled **`VERIFIED_RECEIPT`**.
- Reconcile component identity by `(ecosystem, name, version, scope)` (`runtime`, `dev`, `optional`). A known optional package may be excluded ONLY when its declared platform list excludes the selected consumer platform (review returned exclusion inventory).
- Compare each waiver `expires_on` with `--as-of-date` (expiry day inclusive). Expiry validation alone grants no exception: validate the organization's signed exception record, subject, scope, and owner separately. See [executable release and rollback scenarios](tests/test_supplychain_cli.py) and [SLSA v1.2, Verifying artifacts](https://slsa.dev/spec/v1.2/verifying-artifacts).
