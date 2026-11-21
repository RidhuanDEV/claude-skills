# SBOM Reconciliation, CI SHA Pinning & SLSA Provenance Verification

> Use this playbook when securing CI/CD workflows, pinning third-party GitHub Actions or container base images, generating CycloneDX/SPDX SBOMs from frozen lockfiles, verifying Cosign/SLSA v1.2 provenance, or governing CVE waivers.

## 1. Core Concepts
Supply-chain trust separates **producer claims** from **consumer verification**:
- **Mutable Tag vs Immutable Digest:** Version tags (`@v4`, `:latest`, `:22-alpine`) can be silently overwritten upstream. Immutable `40-char` Git commit SHAs and OCI `@sha256:` digests bind execution to exact content bytes.
- **SLSA v1.2 Consumer Verification Model:** Artifact integrity requires matching the locally computed `sha256` digest against an independently verified CI attestation receipt matching consumer-allowed `trusted_builds` tuples (`issuer`, `builder_id`, `build_type`, `verifier`).

## 2. Technical Rules & Decision Matrix

| Supply-Chain Control | Mechanism / Standard | Pass Criteria |
| :--- | :--- | :--- |
| Lockfile-to-SBOM Parity | CycloneDX 1.5+ / SPDX 2.3 from `package-lock.json` / `uv.lock` / `go.sum` | Zero unpinned transitive drift; explicit `ecosystem`, `name`, `version`, `scope` (`runtime`/`dev`/`optional`) |
| GitHub Actions Hardening | Full 40-char commit SHA + `# vX.Y.Z` comment + least-privilege `permissions` | Zero mutable `@v4` tags; `persist-credentials: false`; `contents: read` default |
| Container Base Pinning | Registry `@sha256:...` digest | Zero floating `:latest` or bare semver tags in production `Dockerfile`s |
| SLSA v1.2 Provenance Gate | Hosted builder attestation + Cosign/Sigstore pre-deploy verify | Local file SHA-256 === verified receipt `subject_sha256` & allowed `(issuer, builder_id, build_type)` |
| Vulnerability Waivers | Signed expiring JSON exception (`expires_on >= assessment_date`) | Explicit `cve_id`, `purl`, `compensating_control`, `owner`, `signed_approval_ref` |

## 3. Implementation Examples

### Hardened GitHub Actions CI + Frozen Lockfile + SHA Pinning
```yaml
name: verified-release-build
on:
  push:
    tags: ["v*"]

permissions: {} # Fail-closed top-level permissions

jobs:
  build-and-attest:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      id-token: write
      attestations: write
    steps:
      - uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683 # v4.2.2
        with:
          persist-credentials: false

      - uses: actions/setup-node@49933ea5288caeca8642d1e84afbd3f7d6820020 # v4.4.0
        with:
          node-version: "22"

      - run: npm ci --ignore-scripts
      - run: npx @cyclonedx/cyclonedx-npm --output-file sbom.cdx.json
      - uses: actions/attest-build-provenance@c074443f1aee8d4aeeae555aebba3282517141b2 # v2.2.3
        with:
          subject-path: "dist/release-artifact.tar.gz"
```

### Cosign Pre-Deploy Provenance Verification & Expiring Waiver Schema
```bash
# Consumer-side independent provenance check before deploy (SLSA v1.2)
cosign verify-attestation \
  --type slsaprovenance \
  --certificate-oidc-issuer "https://token.actions.githubusercontent.com" \
  --certificate-identity-regexp "^https://github\\.com/org/repo/\\.github/workflows/release\\.yml@refs/tags/v" \
  "ghcr.io/org/service@sha256:0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
```
```json
{
  "cve_id": "CVE-2026-0001",
  "purl": "pkg:npm/example-lib@1.2.3",
  "scope": "dev",
  "reason": "Vulnerable YAML loader unreachable in browser bundle; used only in docs build.",
  "compensating_control": "CI blocks untrusted markdown frontmatter; upgrade tracked in PLAT-412.",
  "owner": "platform-security",
  "expires_on": "2026-12-31",
  "signed_approval_ref": "sec-board/waivers/2026-041"
}
```

## 4. Best Practices
- Scope internal packages in `.npmrc` (`@company:registry=https://...`) so dependency confusion attacks against public registries cannot hijack private package names.
- Re-run `python -m unittest tests/test_supplychain_cli.py` whenever modifying lockfile adapters, waiver evaluation logic, or consumer trust policies.
- Pass `--ignore-scripts` during untrusted dependency inspection and isolate lifecycle build scripts explicitly when needed.

## 5. Anti-Patterns (`WRONG` vs `RIGHT`)
- **WRONG (Mutable tags & self-asserted PR receipts):** Writing `uses: actions/checkout@v4`, `FROM node:22-alpine`, or trusting `"provenance": { "signer_verified": true }` inside a PR manifest as deployment proof.
  **RIGHT:** Pin full 40-char SHAs / `@sha256:` digests, verify receipts from a consumer-controlled CI verifier, and match `subject_sha256` against the locally hashed artifact bytes.
- **WRONG (Synthesizing `VERIFIED` offline or permanent CVE ignores):** Marking provenance passed when Sigstore/Rekor is unreachable or adding permanent `ignore` flags to `npm audit`.
  **RIGHT:** Record honest status (`OFFLINE` or `NOT_RUN`), require reachability proof for transitive CVEs, and enforce expiring waivers with signed owner approval.

## 6. Production Considerations
- **Reachability First:** Distinguish runtime-reachable exploit paths from `dev`-only tooling or OS-excluded `optional` packages before gating emergency releases.
- **Registry Resilience:** Cache verified artifacts in a private mirror with checksum locking so upstream package unpublishing cannot break emergency security rebuilds.
