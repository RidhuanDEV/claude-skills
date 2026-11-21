# Production Release Execution, Canary Cohorts & Rollback Playbook

> Use this playbook when designing feature-flag kill switches, deterministic canary cohort rollouts, `< 2 min` post-deploy smoke checks, or safe rollback vs forward-fix runbooks.

## 1. Core Concepts
Deploying safely decouples **code rollout** from **feature exposure** and assumes the new binary and old binary will briefly serve traffic side by side:
- **Deterministic Cohort Bucketing:** Canary evaluations hash stable identifiers (`flagKey + ":" + tenantId`) so a user/tenant does not flip between old and new behavior across page reloads.
- **Reversible Rollback Prerequisite:** A binary rollback succeeds cleanly **only if** the previous release (`N-1`) remains schema- and config-compatible with current database state (Expand-Only during deploy).

## 2. Technical Rules & Decision Matrix

| Rollout / Incident Scenario | Strategy to Pick | Abort & Rollback / Containment Rule |
| :--- | :--- | :--- |
| High-risk feature flag launch | **Kill-Switch Flag + Deterministic Cohort (`1% -> 10% -> 50% -> 100%`)** | Flip kill switch `enabled = false` immediately (`< 5s`); zero container redeploy |
| Stateless app / backward-compatible DB (`N-1` safe) | **Blue-Green / Rolling Binary Rollback** | Halt promotion if error rate, latency p95, or readiness fails in cohort window; revert tag |
| Destructive DDL already mutated prod data | **DO NOT Blindly Rollback Binary -> Write Containment + Forward-Fix** | Block stale schema writes, restore/patch forward with incident owner under `L4` approval |
| Dependency / version gate pre-release | **SBOM + Pinned Lockfile + 8-Field Decision Record Check** | Reject release if floating `:latest` tags or unverified dependencies exist |

## 3. Implementation Examples

### Strict-TS Deterministic Canary Cohort Evaluator + Instant Kill Switch
```ts
import { createHash } from "node:crypto";

export interface CanaryFlagRule {
  readonly key: string;
  readonly enabled: boolean; // Instant kill-switch
  readonly rolloutPercent: number; // 0..100
  readonly allowlistedTenants: ReadonlySet<string>;
}

export function isCohortEnabled(rule: CanaryFlagRule, tenantId: string): boolean {
  if (!rule.enabled) return false;
  if (rule.allowlistedTenants.has(tenantId)) return true;
  if (rule.rolloutPercent <= 0) return false;
  if (rule.rolloutPercent >= 100) return true;

  const digest = createHash("sha256").update(`${rule.key}:${tenantId}`).digest();
  // First 4 bytes as unsigned 32-bit int -> uniform bucket 0..99
  const bucket = digest.readUInt32BE(0) % 100;
  return bucket < rule.rolloutPercent;
}
```

### Bounded `< 2 Min` Post-Deploy Read-Only Smoke Verification
```powershell
param(
  [Parameter(Mandatory = $true)][string]$BaseUrl,
  [Parameter(Mandatory = $true)][string]$ExpectedSha
)
$health = Invoke-RestMethod -Uri "$BaseUrl/readyz" -TimeoutSec 5
if ($health.status -ne "ok" -or $health.gitSha -ne $ExpectedSha) {
  throw "SMOKE_FAILED: readiness=$($health.status) sha=$($health.gitSha) expected=$ExpectedSha"
}
Write-Output "SMOKE_PASS: $BaseUrl serving verified revision $ExpectedSha"
```

## 4. Best Practices
- Pair every canary promotion step with explicit minimum observation duration, minimum request sample threshold, and objective abort thresholds (`5xx > baseline + 0.5%`, `p95 latency > SLO`) comparing identical traffic mixes.
- Keep migration PRs strictly Expand-Only before deploying application code that writes new columns; drop deprecated columns in a follow-up cleanup release after confirming rollback safety window elapsed.

## 5. Anti-Patterns (`WRONG` vs `RIGHT`)
- **WRONG (`Math.random()` canary evaluation):** Evaluating `Math.random() * 100 < pct` per HTTP request (breaks session consistency, triggers race conditions across SSR and CSR).
  **RIGHT:** Use deterministic hash bucketing on `(flagKey, stableSubjectId)` + explicit allowlists for staging/pilot cohorts.
- **WRONG (Assuming `kubectl rollout undo` fixes dropped columns or corrupted rows):** Executing blind binary rollback after destructive DDL already dropped legacy columns (`N-1` crashes reading missing columns).
  **RIGHT:** Verify `N-1` data/config compatibility BEFORE rollback; if destructive DDL ran, halt traffic / contain writes and roll forward with emergency backfill + incident owner.

## 6. Production Considerations
- **Execution Approval (`L0` vs `L4`):** Preparing release checklists, SemVer notes, and verifying SBOM/lockfile parity is `L0_READ_ONLY`; tagging releases, running live prod migrations, or promoting production traffic requires explicit 7-part **`L4_HIGH_IMPACT`** Monarch approval (`shadow-monarch/scripts/execution_approval_gate.py`).
