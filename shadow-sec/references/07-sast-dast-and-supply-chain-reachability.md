# 07. SAST, DAST & Supply-Chain Reachability Triage

## 1. Purpose & Activation Conditions
Run disciplined static/dynamic security testing and triage CVE/SCA alerts by **actual runtime reachability & exploitability** rather than drowning teams in noisy scanner counts — while strictly enforcing `L0`–`L4` execution boundaries and handing off deep SBOM/SLSA provenance checks to `/shadow-supplychain`. Load when triaging `npm/pip/go audit` alerts, configuring CI SAST, or scoping authorized DAST.

## 2. Prerequisites
- Committed lockfile (`package-lock.json`, `pnpm-lock.yaml`, `poetry.lock`, `go.sum`), CI pipeline, and explicit written scope before ANY active DAST.

## 3. Technical Principles & Constraints
- **Reachability-First CVE Triage (Signal Over Noise):** Never treat 20 raw scanner alerts identically. Grade every CVE across 4 objective criteria:
  1. **Runtime vs Dev/Build Only:** Is the package shipped in the production runtime artifact, or strictly a local test/linter devDependency?
  2. **Symbol Reachability:** Is the vulnerable function actually imported and invoked by application code (or transitive runtime paths)?
  3. **Untrusted Input Exposure:** Does untrusted external input (HTTP body, uploaded file, URL, webhook, RAG doc) reach that vulnerable code path?
  4. **Existing Mitigations & Exploit Maturity:** Is there an active KEV (CISA Known Exploited Vulnerability) / public exploit, and are compensating controls (`WAF`, `sandbox`, `non-root`) active?
- **Cross-Skill Boundary (`/shadow-supplychain`):** Hand off CycloneDX/SPDX SBOM generation, SLSA provenance attestations, pinned GitHub Actions/Docker digests, typosquatting checks, and license policies to `/shadow-supplychain` (`supplychain_sbom_gate.py`). `/shadow-sec` focuses on runtime exploitability, code-level SAST sinks, and official-first dependency safety (`official_first_verifier.py`).
- **Strict `L0` vs `L3`/`L4` Active-Testing Approval Gate:**
  - `L0_READ_ONLY`: Static code inspection, STRIDE, `semgrep`, `shadow_gate.py`, lockfile audit (`npm audit --json`).
  - `L1_SAFE_VERIFICATION`: Deterministic unit/integration negative security tests against local loopback/ephemeral fixtures.
  - **`L3_RESOURCE_INTENSIVE` / `L4_HIGH_IMPACT` (NEVER auto-run!):** High-volume active fuzzing, aggressive DAST (`sqlmap`, `nuclei`, `zap` active scan), or ANY active security probing against staging/production targets requires explicit written Monarch authorization and isolated target confirmation!

## 4. Architecture & Implementation
```typescript
export interface CveTriageInput {
  readonly cveId: string;
  readonly packageName: string;
  readonly cvssBase: number;
  readonly inProductionRuntime: boolean;
  readonly vulnerableSymbolReachable: boolean;
  readonly exposedToUntrustedInput: boolean;
  readonly inCisaKev: boolean;
}

export type TriagePriority = 'P0_PATCH_IMMEDIATELY' | 'P1_PATCH_THIS_SPRINT' | 'P2_SCHEDULED_UPGRADE' | 'P3_MONITOR_DEV_ONLY';

export function triageCveByReachability(cve: CveTriageInput): TriagePriority {
  if (cve.inProductionRuntime && cve.vulnerableSymbolReachable && (cve.exposedToUntrustedInput || cve.inCisaKev)) {
    return 'P0_PATCH_IMMEDIATELY';
  }
  if (cve.inProductionRuntime && cve.cvssBase >= 7.0) {
    return 'P1_PATCH_THIS_SPRINT';
  }
  if (cve.inProductionRuntime) {
    return 'P2_SCHEDULED_UPGRADE';
  }
  return 'P3_MONITOR_DEV_ONLY';
}
```
Read-only CI SAST & lockfile hygiene commands (`L0`/`L1`):
```powershell
# Safe read-only static checks & lockfile audit (zero active external probing)
python "shadow-quality/scripts/shadow_gate.py" --repo .
python "shadow-monarch/scripts/official_first_verifier.py" --self-test
# Ecosystem-native read-only advisories (run per repo stack):
# npm audit --omit=dev --audit-level=high
# pip-audit --strict
# govulncheck ./...   # Native Go call-graph reachability analyzer!
```

## 5. Platform / Vendor Variations
| Ecosystem | Native Reachability / SAST Tool | Strength |
| :--- | :--- | :--- |
| **Go** | `govulncheck ./...` | True call-graph symbol reachability built into Go toolchain |
| **TypeScript / JS / Python / Multi-Lang** | `Semgrep` + `CodeQL` + `OSV-Scanner` | Fast custom AST rules blocking `$queryRawUnsafe`, `exec`, `eval`, `dangerouslySetInnerHTML` |
| **Containers & IaC** | `Trivy` / `Grype` + `Hadolint` | Catches vulnerable OS base packages & root container misconfigs |

## 6. Decision Matrix & Trade-Offs
| Triage Tier | SLA Target | Action |
| :--- | :---: | :--- |
| **`P0_PATCH_IMMEDIATELY`** (Runtime + Reachable + Untrusted Input/KEV) | `< 24–48h` | Patch/upgrade immediately, add regression fixture, deploy hotfix |
| **`P1_PATCH_THIS_SPRINT`** (Runtime High CVSS, unconfirmed reachability) | `7–14 days` | Upgrade cleanly in sprint; document compensating control if blocked |
| **`P2_SCHEDULED_UPGRADE`** (Runtime Med/Low) | `30 days` | Batch into planned maintenance window |
| **`P3_MONITOR_DEV_ONLY`** (Dev/build-only tool, zero runtime shipping) | `30–90 days` | Upgrade during routine tooling refresh; never page on-call at 02:00 |

## 7. Real Production Scenario
`npm audit` blocks a Friday release with 19 alerts: 18 `High` ReDoS advisories inside a dev-only Storybook webpack plugin and 1 `Critical` RCE inside a runtime PDF parser invoked directly on customer uploads. Naive alert sorting stalls engineering for 3 days upgrading Storybook while leaving the PDF RCE exposed! Applying `triageCveByReachability` flags the PDF parser as `P0_PATCH_IMMEDIATELY` (patched & verified with a malicious PDF regression fixture in 2 hours) while queuing the 18 dev-only upgrades cleanly into next sprint's maintenance ticket.

## 8. Failure Modes & Edge Cases
- **WRONG:** Running `npm audit fix --force` blindly in production repos (installs breaking major versions and breaks runtime behavior without verification!).
- **RIGHT:** Inspect exact advisories, upgrade targeted packages cleanly via lockfile update + full regression test suite, and verify via `official_first_verifier.py`.
- **WRONG:** Accepting a user request `"run sqlmap against our live site right now"` without explicit `L3`/`L4` scope verification and isolated staging target.
- **RIGHT:** Refuse unauthorized live exploitation/fuzzing, run `L0` static analysis + sandboxed unit tests, and request formal authorization + staging target before any active DAST.

## 9. Testing & Verification
- Run `python shadow-sec/scripts/appsec_control_verifier.py --check-finding-report <report.json>` ensuring `unapproved_live_probing_executed: false`.
- Verify every P0 vulnerability fix ships with a failing-before / passing-after regression test in local sandbox fixtures.

## 10. Operational Considerations
- Track vulnerability **waivers** with mandatory owner, technical justification, compensating control, and hard expiry date (`<= 30–90 days`) — never silence an alert permanently with an undated ignore flag!

## 11. Authoritative References
- NIST SP 800-218 (SSDF) — `PW.4` & `RV.1`–`RV.2` (`https://csrc.nist.gov/pubs/sp/800/218/final`).
- OSV (Open Source Vulnerabilities) Schema & Scanner (`https://osv.dev/`).
- CISA Known Exploited Vulnerabilities (KEV) Catalog (`https://www.cisa.gov/known-exploited-vulnerabilities-catalog`).

## 12. Limitations & When NOT to Use
- Static SAST tools excel at pattern-based sinks (`SQLi`, `exec`, `XSS`, hardcoded secrets) but routinely miss subtle **business-logic and multi-tenant authorization flaws (`BOLA`/`IDOR`)** — always pair SAST with STRIDE (`01`) and negative authz matrix tests (`shadow-auth`).
