# 02 — CI 40-Char Commit SHA Pinning, Container Digest Pinning & Runner Isolation

## 1. Purpose & Activation Conditions
Harden CI/CD build workflows and Dockerfiles against **mutable tag hijacking** (the exact vector behind major GitHub Actions compromises like `tj-actions/changed-files`) by pinning every third-party CI action to a **40-character immutable Git commit SHA**, pinning every production container base image to an **`@sha256:` OCI digest**, enforcing fail-closed workflow `permissions: {}`, and isolating release runners. Activate whenever writing or auditing GitHub Actions, GitLab CI, or production `Dockerfile`s.

## 2. Prerequisites
- Active CI workflows (`.github/workflows/*.yml`, `.gitlab-ci.yml`) and production `Dockerfile` / `docker-compose.prod.yml`.

## 3. Technical Principles & Constraints
- **Mutable Version Tags Are Moveable Pointers — NOT Immutable Releases:**
  - `uses: third-party/action@v4` or `FROM node:22-alpine` can be silently force-pushed by a compromised maintainer account tomorrow to execute credential-stealing malware inside your CI runner!
  - **GitHub Actions Mandatory Rule:** Pin EVERY external action to its full **40-character commit SHA** with a human-readable trailing version comment (`uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683 # v4.2.2`) so Dependabot/Renovate can still propose audited updates cleanly!
  - **Container Image Mandatory Rule:** Pin EVERY production `FROM` base image and deployed image to its exact **`@sha256:<64-hex>`** digest (`FROM node:22.11-alpine@sha256:...`). Zero `:latest` or bare floating tags in production!
- **Least-Privilege Fail-Closed CI Permissions:**
  - Declare top-level **`permissions: {}`** (zero default token rights!) in every GitHub Actions workflow, granting minimal job-scoped permissions (`contents: read`, plus `id-token: write` & `attestations: write` ONLY inside the isolated release/sign job!).
  - Always set **`persist-credentials: false`** on `actions/checkout` so compromised build scripts cannot read the `GITHUB_TOKEN` out of `.git/config`!
- **Prevent Script Injection (`pull_request_target` & `${{ github.event.* }}`):**
  - NEVER interpolate untrusted PR titles, branch names, or commit messages directly inside `run: echo "${{ github.event.pull_request.title }}"` (arbitrary shell command execution in CI!) — pass untrusted metadata strictly via an `env:` variable quoted inside the shell script!
  - NEVER check out and execute untrusted fork PR code inside a `pull_request_target` job carrying write tokens or production secrets!
- **Install Hygiene (`--ignore-scripts` & Isolated Release Builders):**
  - Run `npm ci --ignore-scripts` when auditing untrusted dependency updates or when native postinstall scripts aren't needed; execute production release builds on ephemeral hosted CI runners (NEVER on a developer's dirty laptop or a shared persistent VM where prior builds leave secret residue!).

## 4. Architecture & Implementation

```yaml
# Hardened Release CI Workflow: Fail-Closed Permissions + 40-Char SHA Pinning + Frozen Lockfile + Attestation
name: hardened-release-build
on:
  push:
    tags: ["v*"]

permissions: {} # Fail-closed top-level default (0 ambient permissions!)

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
      - run: npm run build
      - run: npx @cyclonedx/cyclonedx-npm --output-file sbom.cdx.json

      - uses: actions/attest-build-provenance@c074443f1aee8d4aeeae555aebba3282517141b2 # v2.2.3
        with:
          subject-path: "dist/release-artifact.tar.gz"
```

### CI & Image Pinning Control Matrix

| Attack Vector | Vulnerable Pattern | Hardened Control |
| :--- | :--- | :--- |
| **Compromised GitHub Action tag re-point** | `uses: org/tool@v2` | `uses: org/tool@<40-char-sha> # v2.4.1` |
| **Compromised Docker Hub `:22-alpine` tag** | `FROM node:22-alpine` | `FROM node:22.11-alpine@sha256:<64-hex>` |
| **Malicious build script stealing `GITHUB_TOKEN`** | Default `write-all` + `persist-credentials: true` | Top-level `permissions: {}` + `persist-credentials: false` |
| **Fork PR title RCE in CI shell** | `run: echo ${{ github.event.pull_request.title }}` | Pass via `env: PR_TITLE: ${{ ... }}` and quote `"$PR_TITLE"` |
| **Malicious `postinstall` hook in npm package** | Blind `npm install` on unverified PR | `npm ci --ignore-scripts` + inspect lifecycle scripts |

## 5. Platform/Vendor Variations
- **GitLab CI / Bitbucket Pipelines:** Pin runner images (`image: node:22.11-alpine@sha256:...`), pin remote `include:` templates by exact commit `ref:` SHA (not `main`), and mask/protect release variables strictly to protected tags.
- **Automated Safe Updates (Renovate / Dependabot):** Configure Renovate `pinDigests: true` and GitHub Actions SHA pinning so security updates remain low-friction without sacrificing digest immutability.

## 6. Decision Matrix & Trade-Offs

| Pinning Policy | Protection Against Tag Hijack | Maintenance Effort | Recommendation |
| :--- | :---: | :---: | :--- |
| **Floating `:latest` / `@main`** | **Zero** | Fragile (random CI breaks!) | **FORBIDDEN** |
| **SemVer Tag (`@v4`, `:22-alpine`)** | **Zero** (maintainer/attacker can move tag!) | Low | Acceptable only in throwaway scratch demos |
| **40-Char Commit SHA / `@sha256:` Digest + `# vX.Y.Z`** | **Maximum** (cryptographic content lock) | Low (with Renovate/Dependabot) | **Mandatory** for all production & release CI |

## 7. Real Production Scenario
When a widely used third-party GitHub Action had its `@v35` tag retroactively re-pointed to a commit that dumped runner memory secrets into CI logs, repositories pinned to `@v35` immediately leaked cloud credentials — while repositories pinned to full 40-char commit SHAs with `permissions: {}` and `persist-credentials: false` suffered **zero** exposure and zero secret rotation downtime!

## 8. Failure Modes & Edge Cases
- **WRONG:** Leaving `permissions: write-all` on a PR test workflow or using `pull_request_target` to run `npm test` on untrusted external PRs (allows any random GitHub user to exfiltrate repository secrets!).
  **RIGHT:** Use `pull_request` (unprivileged read-only token, zero secrets) for untrusted PR builds, set top-level `permissions: {}`, and keep signing secrets strictly in isolated tag/release jobs.
- **WRONG:** Pinning a SHA without keeping the `# vX.Y.Z` version comment (makes human code review and Dependabot updates unreadable).
  **RIGHT:** Always pair the 40-char SHA with `# vX.Y.Z`.

## 9. Testing & Verification
- Audit `.github/workflows/*.yml` with `actionlint` / `zizmor` / `pinact` in CI to fail on any unpinned third-party action, missing `permissions: {}`, or `${{ github.event.* }}` shell interpolation.
- Verify `shadow-ops/scripts/ops_hardening_verifier.py` catches floating `:latest` Docker images.

## 10. Operational Considerations
- Pair CI pinning with **egress monitoring** (e.g., StepSecurity `harden-runner`) on high-security release workflows so unexpected outbound network calls during `npm ci` / `build` trigger immediate alerts.

## 11. Authoritative References
- OWASP CI/CD Security Top 10 & GitHub Actions Security Hardening Guide.
- OpenSSF Scorecard — *Pinned-Dependencies & Token-Permissions Checks*.
- `shadow-ops/references/vendor/OWASP_CI_CD_Security_Cheat_Sheet.md`.

## 12. Limitations & When NOT to Use
- Pinning an action SHA does NOT audit the safety of the code *inside* that pinned commit — always inspect third-party action popularity, maintainer reputation, and source code before adopting it the first time (`03`).
