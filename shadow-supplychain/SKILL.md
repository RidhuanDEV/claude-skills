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
python "shadow-supplychain/scripts/supplychain_sbom_gate.py" --verify manifest.json --policy consumer-policy.json --artifact release.bin --receipt verifier-result.json --as-of-date 2026-11-19
```

## Artifact-specific release decision

Separate the producer's inventory from the consumer's trust policy and CI verification receipt. Inspect the repository's existing signer verification step, confirm which identity checks it actually ran, and normalize only its observed output. Read the receipt from a consumer-controlled CI channel. A receipt supplied by the artifact author, an editable PR file or a failed verifier cannot establish signer trust. Keep the original signature, upstream output, verifier version, CI run identity and policy revision for the reviewer. This gate hashes the artifact bytes locally and reconciles evidence; cryptographic signature verification remains with that independent verifier.

- Provide an ordered CLI handoff: normalized manifest, actual release artifact, consumer policy, verifier receipt, and the evaluation date for any vulnerability waiver. The manifest can contain historical `provenance.signer_verified`; this declaration alone yields `INCOMPLETE`.
- In the consumer policy, `trusted_builds` is an array of allowed **tuples** of `issuer`, `builder_id`, `build_type` and `verifier`. An optional `platform` describes the release profile. The verifier receipt contains those four values, `status: VERIFIED` and a lowercase hex `subject_sha256`. The local artifact hash must match that subject. For offline or unavailable verification, record `OFFLINE` or `NOT_RUN`; never synthesize a successful receipt. The verified dimension is labeled `VERIFIED_RECEIPT`. Any SLSA level, builder isolation, external build parameters and vulnerability reachability need their own evidence.
- Reconcile component identity by ecosystem, name, version and scope (runtime, dev or optional). For heterogeneous lockfiles, adapters must supply ecosystem on every record. Legacy name/version records use an unspecified ecosystem and default runtime scope. A known optional package may be excluded only when its declared platform list excludes the selected consumer platform. Review the returned exclusion inventory. For ambiguous aliases, variant IDs or multiple packages with identical normalized coordinates, reconcile source/package identifiers before producing the manifest.
- If waivers exist, compare each expiry with the independently supplied assessment date (expiry day inclusive). Expiry validation alone grants no exception: obtain the organization's signed exception record and validate its subject, scope and owner separately.

[Executable release and rollback scenarios](tests/test_supplychain_cli.py) distinguish a correctly bound fixture, identical name with changed bytes, untrusted issuer/builder pairing, missing receipt, offline verification and expired waiver. Apply the consumer trust model in [SLSA v1.2, Verifying artifacts](https://slsa.dev/spec/v1.2/verifying-artifacts).
