# 01 — CycloneDX/SPDX SBOM Generation, Lockfile Parity & Reachability Triage

## 1. Purpose & Activation Conditions
Generate accurate **CycloneDX 1.5+ (current 1.7) / SPDX 2.3+ (current 3.0.1) Software Bills of Materials (SBOMs)** directly from frozen lockfiles, prove **1:1 component parity** across `(ecosystem, name, version, scope)`, enforce **license compliance**, and prioritize vulnerabilities by **production runtime reachability** instead of noisy dev-only alert storms. Activate before every production release (`/shadow-release`), during client delivery (`/shadow-handover`), or when auditing third-party dependencies.

## 2. Prerequisites
- Frozen deterministic lockfile committed to Git (`package-lock.json`, `pnpm-lock.yaml`, `uv.lock`, `poetry.lock`, `go.sum`, `Cargo.lock`, `composer.lock`).
- Target consumer platform declared (`linux/amd64`, `linux/arm64`) so optional OS-specific dependencies reconcile accurately.

## 3. Technical Principles & Constraints
- **SBOM Must Derive From the Resolved Lockfile — NEVER Hand-Written Manifests:** Direct manifests (`package.json`, `pyproject.toml`) omit 90% of transitive dependencies where real supply-chain compromises hide! Always generate SBOMs from the frozen lockfile (`npm ci` / `uv sync --frozen` state) or built OCI image.
- **4-Tuple Component Identity Reconciliation (`ecosystem`, `name`, `version`, `scope`):**
  - Reconcile every SBOM component 1:1 against the resolved lockfile (`0` phantom packages, `0` missing runtime packages).
  - Tag every component with explicit **`scope`** (`runtime`, `dev`, or `optional`) and **`purl`** (Package URL, e.g., `pkg:npm/zod@3.23.8`).
  - **Optional Platform Exclusion Rule:** A known `optional` package (e.g., `fsevents` on macOS) may be excluded from a Linux release SBOM **ONLY** when its declared platform list explicitly excludes the consumer platform — and MUST appear in the returned exclusion inventory for auditability!
  - Reconcile ambiguous aliases or duplicate normalized coordinates BEFORE generating the release manifest (`supplychain_sbom_gate.py`).
- **Runtime Reachability First (Signal Over Alert Fatigue):** A Critical CVE inside a `dev`-only docs linter that never ships in the production container is NOT equivalent to a reachable RCE inside an internet-facing JWT/XML parser! Classify findings as: (1) **Runtime Reachable** (block release / patch immediately), (2) **Runtime Present / Unreachable** (upgrade soon or time-bounded signed waiver with compensating control), (3) **Dev/Build-Only** (track & upgrade cleanly without panicking hotfix deploys).
- **License Policy Screening:** Automatically flag copyleft viral licenses (`AGPL-3.0`, `GPL-3.0`, `SSPL`) or `UNKNOWN`/unlicensed packages inside proprietary commercial products BEFORE adoption or client BAST delivery (`/shadow-handover`).

## 4. Architecture & Implementation

### Polyglot Lockfile -> SBOM Generator Matrix

| Ecosystem | Frozen Lockfile | Standard CycloneDX / SPDX Generator | Frozen Install Guard |
| :--- | :--- | :--- | :--- |
| **Node.js / TS** | `package-lock.json` / `pnpm-lock.yaml` | `@cyclonedx/cyclonedx-npm`, `cdxgen`, `syft` | `npm ci --ignore-scripts` / `pnpm install --frozen-lockfile` |
| **Python** | `uv.lock` / `poetry.lock` | `cyclonedx-py`, `syft` | `uv sync --frozen --no-dev` |
| **Go** | `go.mod` + `go.sum` | `cyclonedx-gomod`, `syft` | `go build -mod=readonly` |
| **Rust** | `Cargo.lock` | `cargo-cyclonedx` / `cargo-auditable` | `cargo build --locked` |
| **PHP** | `composer.lock` | `cyclonedx/cyclonedx-php-composer` | `composer install --no-dev --no-interaction` |
| **OCI Container Image** | Built `@sha256:` image | `syft <image@sha256:...> -o cyclonedx-json` | Scan exact promoted digest (never `:latest`!) |

```ts
// Strict TypeScript Lockfile-to-SBOM Coordinate Parity Checker (0 any, 0 casts)
export interface PackageCoordinate {
  readonly ecosystem: string
  readonly name: string
  readonly version: string
  readonly scope: 'runtime' | 'dev' | 'optional'
  readonly platforms?: readonly string[]
}

export interface ParityReport {
  readonly missingFromSbom: readonly string[]
  readonly extraInSbom: readonly string[]
  readonly excludedOptional: readonly string[]
  readonly passed: boolean
}

function coordKey(c: PackageCoordinate): string {
  return `${c.ecosystem.toLowerCase()}:${c.name}@${c.version}`
}

export function reconcileLockfileAndSbom(
  lockfilePkgs: readonly PackageCoordinate[],
  sbomPkgs: readonly PackageCoordinate[],
  targetPlatform: string,
): ParityReport {
  const sbomSet = new Set(sbomPkgs.map(coordKey))
  const lockSet = new Set<string>()
  const missingFromSbom: string[] = []
  const excludedOptional: string[] = []

  for (const pkg of lockfilePkgs) {
    const key = coordKey(pkg)
    if (pkg.scope === 'optional' && pkg.platforms && !pkg.platforms.includes(targetPlatform)) {
      excludedOptional.push(key)
      continue
    }
    lockSet.add(key)
    if (pkg.scope === 'runtime' && !sbomSet.has(key)) {
      missingFromSbom.push(key)
    }
  }
  const extraInSbom = sbomPkgs.map(coordKey).filter((k) => !lockSet.has(k))
  return {
    missingFromSbom,
    extraInSbom,
    excludedOptional,
    passed: missingFromSbom.length === 0 && extraInSbom.length === 0,
  }
}
```

## 5. Platform/Vendor Variations
- **Heterogeneous Monorepos (Node + Python + Go):** Ensure every SBOM/manifest adapter emits an explicit `ecosystem` field (`npm`, `pypi`, `golang`) on every component record so identically named packages across ecosystems never collide during reconciliation!
- **Client BAST / Government SPBE Delivery (`/shadow-handover`):** Deliver BOTH machine-readable `sbom.cdx.json` AND a human-readable license & CVE disposition summary attached to the exact release Git SHA.

## 6. Decision Matrix & Trade-Offs

| SBOM Format | Ecosystem Strength | Interop Standard | When to Choose |
| :--- | :--- | :--- | :--- |
| **CycloneDX (`1.7` current; `1.5`+ minimum, JSON)** | Application security, VEX/reachability, OWASP native | ECMA-424 (2nd edition = 1.7) | **Default** for AppSec, CI release gates & VEX |
| **SPDX (`3.0.1` current; `2.3` JSON still common)** | Legal/IP licensing compliance, Linux Foundation | ISO/IEC 5962:2021 (= SPDX 2.2.1) | Regulated legal/government contracts requesting SPDX |

## 7. Real Production Scenario
During a banking vendor audit, a team submitted a manually typed spreadsheet of 18 top-level `package.json` packages as their "SBOM." Automated scanning of the actual production container with `syft` revealed 312 transitive packages — including an outdated `axios` transitive copy carrying a reachable SSRF vulnerability and an `AGPL-3.0` PDF library prohibited by the client's IP clause! Switching to CI-generated CycloneDX SBOMs reconciled against `package-lock.json` via `supplychain_sbom_gate.py` plus automated license screening prevented both compliance and security failures before client UAT.

## 8. Failure Modes & Edge Cases
- **WRONG:** Generating an SBOM before running `npm ci`, or excluding `dev` vs `runtime` scopes blindly so `0` runtime packages are verified.
  **RIGHT:** Generate SBOM from the exact resolved lockfile/image, tag `runtime`/`dev`/`optional` explicitly, and verify 1:1 coordinate parity via `supplychain_sbom_gate.py`.
- **WRONG:** Treating `npm audit` output of `47 high vulnerabilities` in dev-only test tooling identically to 1 reachable runtime RCE (causes developers to ignore ALL security alerts!).
  **RIGHT:** Triage by runtime reachability + exploitability (VEX), patch runtime reachable CVEs urgently, and govern unreachable/dev exceptions via expiring signed waivers (`04`).

## 9. Testing & Verification
- Run `python shadow-supplychain/scripts/supplychain_sbom_gate.py --self-test` and `python -m unittest discover -s shadow-supplychain/tests -v`.
- Verify every PR updating lockfiles regenerates and reconciles the SBOM cleanly in CI.

## 10. Operational Considerations
- Archive the exact `sbom.cdx.json` alongside every released container digest so when a new zero-day CVE (like Log4Shell or XZ) drops months later, you can answer "Are we affected?" across all production services in `< 60 seconds`!

## 11. Authoritative References
- OWASP CycloneDX Specification (v1.7, `https://cyclonedx.org/news/cyclonedx-v1.7-released`; v1.5+ minimum) & Package URL (`purl`) Specification.
- SPDX 3.0.1 (ISO/IEC 5962:2021 still equals SPDX 2.2.1) & NTIA Minimum Elements for an SBOM.
- `shadow-supplychain/methodologies/SBOM-SLSA-PROVENANCE-AND-LOCKFILE-INTEGRITY.md`.

## 12. Limitations & When NOT to Use
- An SBOM proves **what components are declared**, NOT that the binary wasn't tampered with after build — always pair SBOM parity with SLSA v1.2 cryptographic provenance verification (`04`)!
