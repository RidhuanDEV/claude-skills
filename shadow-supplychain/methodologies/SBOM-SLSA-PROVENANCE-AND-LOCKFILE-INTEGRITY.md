# SBOM Reconciliation, SLSA Provenance & Lockfile Integrity Methodology

## 1. Adversarial Supply-Chain Scenarios
| Threat | Detection Signal | Required Defense |
|---|---|---|
| **Malicious Lookalike (Typosquatting)** | Package name within edit distance `1` of popular ecosystem lib (`lodash` vs `1odash`, `reqeusts` vs `requests`) | Flag near-match dependencies; require manual registry provenance inspection |
| **Dependency Confusion** | Unscoped internal package name resolves against public npm/PyPI | Enforce scoped namespaces (`@org/*`) mapped strictly to private registry (`npmrc` / pip index-url) |
| **Stale / Unsynced Lockfile** | `package.json` updated without regenerating `package-lock.json` (`--frozen-lockfile` fails) | Enforce `--frozen-lockfile` / `npm ci` in CI; reject SBOMs not matching lockfile exact versions |
| **Floating Build Inputs** | GitHub Action pinned to `@v4`/`@main` or Docker base image `:latest` | Pin full 40-char commit SHA for CI actions and `sha256:...` digest for container base images |
| **Unverifiable Signer / Expired Waiver** | Artifact signature missing/untrusted or CVE waiver past `expires_at` | Block release (`FAIL`) until valid signer provenance & active non-expired waiver exist |
