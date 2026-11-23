# 03 — Feature-Flag Kill Switches, Deterministic Canaries & `< 2 Min` Smoke Probes

## 1. Purpose & Activation Conditions
Decouple **code deployment** from **customer feature exposure** using **instant kill-switch feature flags**, **deterministic hash canary cohorts (`1% -> 10% -> 50% -> 100%`)**, and **bounded `< 2 minute` post-deploy read-only smoke verification** with objective abort thresholds. Activate when launching high-risk features, setting up progressive delivery, or writing post-deploy verification scripts.

## 2. Prerequisites
- Readiness endpoint (`/readyz` or `/health/ready`) exposing exact deployed `gitSha` / `releaseVersion` and mandatory dependency status (`shadow-observe`).
- Baseline error rate and latency metrics sliced by `service.version` or canary cohort.

## 3. Technical Principles & Constraints
- **Deterministic Hash Bucketing — NEVER `Math.random()`:** Evaluate canary eligibility by hashing a stable compound key (`sha256(flagKey + ":" + stableSubjectId) -> uint32 % 100 < rolloutPercent`), plus explicit allowlists for internal QA/pilot tenants. Why? Per-request `Math.random()` makes a user see the new checkout UI on load #1, the old API on submit #2, and breaks SSR/CSR hydration!
- **Instant Kill-Switch Flag (`< 5s` Blast Containment):** High-risk features (new payment rail, new search reranker, redesigned checkout) MUST ship dark (`rolloutPercent: 0` or `enabled: false`) behind a runtime toggle so flipping `enabled: false` stops customer pain in `< 5 seconds` without waiting 4 minutes for a container rollback!
- **Flag Debt Hygiene:** Every release flag MUST carry an explicit owner and expiration ticket (`remove within 30 days of 100% rollout`) so stale `if (flag)` branches don't rot the codebase forever.
- **Objective Canary Promotion & Abort Criteria:**
  - Compare candidate cohort against a **matched healthy control cohort** (identical client version, route, and traffic mix — NEVER compare an internal employee pilot cohort against peak evening mobile traffic!).
  - Require minimum observation window (`>= 10–15 min`) AND minimum sample size (`>= 500` requests) before promoting `1% -> 10% -> 50% -> 100%`.
  - Pre-arm hard abort thresholds (e.g., `5xx rate > baseline + 0.5%`, `p95 latency > SLO + 25%`, or readiness check fails -> **HALT promotion immediately**!).
- **Bounded `< 2 Minute` Post-Deploy Smoke Check:** Immediately after deploy completes: (1) verify `/readyz` returns `200` AND matches exact `expectedSha`, (2) inspect last 50 container/systemd logs for zero startup errors, and (3) run read-only smoke checks on critical public + authenticated canary journeys.

## 4. Architecture & Implementation

```ts
// Strict TypeScript Deterministic Canary Cohort Evaluator + Instant Kill-Switch (0 any, 0 casts)
import { createHash } from 'node:crypto'

export interface CanaryFlagRule {
  readonly key: string
  readonly enabled: boolean // Instant kill-switch (<5s disable)
  readonly rolloutPercent: number // 0..100
  readonly allowlistedTenants: ReadonlySet<string>
  readonly denylistedTenants: ReadonlySet<string>
}

export function isCanaryCohortEnabled(rule: CanaryFlagRule, tenantId: string): boolean {
  if (!rule.enabled) return false
  if (rule.denylistedTenants.has(tenantId)) return false
  if (rule.allowlistedTenants.has(tenantId)) return true
  if (rule.rolloutPercent <= 0) return false
  if (rule.rolloutPercent >= 100) return true

  const digest = createHash('sha256').update(`${rule.key}:${tenantId}`).digest()
  const bucket = digest.readUInt32BE(0) % 100
  return bucket < rule.rolloutPercent
}

export interface CanaryComparisonInput {
  readonly canarySamples: number
  readonly minRequiredSamples: number
  readonly canary5xxRatio: number
  readonly control5xxRatio: number
  readonly maxAllowed5xxDelta: number
  readonly canaryP95Ms: number
  readonly sloP95Ms: number
}

export type CanaryDecision = 'HOLD_INSUFFICIENT_SAMPLES' | 'ABORT_REGRESSION' | 'PROMOTE_SAFE'

export function evaluateCanaryGate(input: CanaryComparisonInput): CanaryDecision {
  if (input.canarySamples < input.minRequiredSamples) {
    return 'HOLD_INSUFFICIENT_SAMPLES'
  }
  const errorDelta = input.canary5xxRatio - input.control5xxRatio
  if (errorDelta > input.maxAllowed5xxDelta || input.canaryP95Ms > input.sloP95Ms) {
    return 'ABORT_REGRESSION'
  }
  return 'PROMOTE_SAFE'
}
```

### Bounded `< 2 Min` Post-Deploy Read-Only Smoke Probe (PowerShell)
```powershell
param(
  [Parameter(Mandatory = $true)][string]$BaseUrl,
  [Parameter(Mandatory = $true)][string]$ExpectedSha
)
$ErrorActionPreference = "Stop"
$health = Invoke-RestMethod -Uri "$BaseUrl/readyz" -TimeoutSec 5
if ($health.status -ne "ready" -and $health.status -ne "ok") {
  throw "SMOKE_FAILED: readiness status=$($health.status)"
}
if ($health.releaseSha -ne $ExpectedSha) {
  throw "SMOKE_FAILED: deployed sha=$($health.releaseSha) expected=$ExpectedSha"
}
Write-Output "SMOKE_PASS: $BaseUrl serving verified revision $ExpectedSha"
```

## 5. Platform/Vendor Variations
- **Progressive Delivery Controllers (Argo Rollouts / Flagger / AWS CodeDeploy):** Automate canary traffic shifting (`5% -> 25% -> 50% -> 100%`) directly tied to Prometheus SLO queries (`shadow-observe`) with automatic halt/rollback on threshold breach.
- **Blue-Green VPS / Docker Compose Deploys:** Spin up `api-green` on internal port, run `< 2 min` read-only smoke check against `api-green` BEFORE switching Nginx/Caddy upstream, keep `api-blue` warm for 15–30 minutes for instant 1-second traffic switchback!
- **Feature Flag Resiliency:** Always supply safe hardcoded default values in code when the flag store/Redis is unreachable (`shadow-resilience`), and log active flag variant in canonical wide events so incident traces slice by flag state!

## 6. Decision Matrix & Trade-Offs

| Rollout Strategy | Recovery Speed | Infra Complexity | Best Fit |
| :--- | :--- | :--- | :--- |
| **Kill-Switch Feature Flag + Deterministic Cohort** | **`< 5 seconds`** | Very Low (app-level) | High-risk UX/business logic changes, mobile-backed features |
| **Blue-Green Upstream Switch** | **`< 10 seconds`** | Low (Nginx/Caddy + 2 containers) | VPS / Docker Compose production deployments |
| **Automated K8s Canary (`1% -> 10% -> 100%`)** | `< 30 seconds` | Medium–High (Ingress/Rollouts) | High-RPS multi-pod Kubernetes services |
| **Big-Bang 100% Replace (No Flag, No Warm Prev)** | Slow (`5–15 min` rebuild) | Minimal | **AVOID** for customer-facing production services |

## 7. Real Production Scenario
A SaaS billing platform rolled out a rewritten tax-calculation engine behind `isCanaryCohortEnabled` at `5%` of tenants (plus internal test org in `allowlistedTenants`). Within 12 minutes (`1,240` invoices), canary monitoring caught a `0.8%` validation error delta on regional tax codes (`ABORT_REGRESSION`). Ops flipped `enabled: false` in 3 seconds — zero downtime, zero binary rollback needed, and 95% of customers never experienced the bug!

## 8. Failure Modes & Edge Cases
- **WRONG:** Evaluating `Math.random() * 100 < pct` inside a React component or HTTP handler (users flicker randomly between variants across requests and corrupt A/B/canary telemetry!).
  **RIGHT:** Use deterministic SHA-256 hash bucketing keyed by `(flagKey, stableSubjectId)`.
- **WRONG:** Promoting a canary from `1%` to `100%` after only `12` requests (`0/12` errors has massive statistical uncertainty!) or checking `/health` instead of verifying `releaseSha === ExpectedSha` + real dependency readiness.
  **RIGHT:** Enforce `minRequiredSamples` (`HOLD_INSUFFICIENT_SAMPLES`) and verify exact deployed `releaseSha` in `< 2 min` smoke probes.

## 9. Testing & Verification
- Unit-test `isCanaryCohortEnabled`: assert identical `(key, tenantId)` ALWAYS returns the same boolean across 1,000 calls, `enabled: false` always overrides `allowlistedTenants`, and `rolloutPercent: 10` activates roughly `~10%` across 10,000 synthetic tenant IDs.
- Verify `release_readiness_verifier.py` rejects `bucketing: "random"` and empty `abort_thresholds`.

## 10. Operational Considerations
- Schedule automated cleanup tickets removing graduated release flags once `100%` rollout has been stable for 14–30 days so flag permutations don't multiply testing complexity.

## 11. Authoritative References
- Pete Hodgson (MartinFowler.com) — *Feature Toggles (Release, Ops & Permission Toggles)*.
- Google SRE Workbook — *Canarying Releases*.
- Argo Rollouts & Progressive Delivery Patterns.

## 12. Limitations & When NOT to Use
- Do NOT use a feature flag as a substitute for security authorization (`shadow-auth`) or for hiding incomplete destructive schema migrations (`02`).
- Note that product-growth **A/B experiments** (requiring CUPED, SRM checks, and exposure tracking) belong in `/shadow-analytics` — release canaries here strictly guard operational stability!
