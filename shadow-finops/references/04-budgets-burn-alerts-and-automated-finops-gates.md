# 04. Budgets, Anomaly Burn Alerts, CI Cost Gates & FinOps Operating Cadence

## 1. Purpose & Activation Conditions
Use this playbook in the **Operate** phase of the FinOps lifecycle to prevent silent billing runaways before month-end invoices land. One misconfigured recursive LLM agent loop, runaway Kubernetes HPA, or unpartitioned analytics query can burn a full month's budget in 4 hours; automated **multi-threshold budget alerts**, **cost-anomaly detection**, **hard LLM quota circuit breakers**, and **CI FinOps static gates (`finops_cost_auditor.py`)** turn FinOps from reactive invoice shock into continuous engineering hygiene.

Activate this playbook when:
- Configuring cloud/AI budget thresholds (`50%`, `80%`, `100%` actual & forecasted) and anomaly escalation playbooks.
- Wiring `finops_cost_auditor.py --audit .` into pull-request CI pipelines.
- Establishing monthly FinOps engineering-finance review rituals and ephemeral environment teardown policies.

## 2. Prerequisites
- FOCUS normalized spend feed (`01-finops-framework-focus-schema-and-unit-economics.md`) and observability alert routing (`/shadow-observe`).
- Deterministic auditor [`../scripts/finops_cost_auditor.py`](../scripts/finops_cost_auditor.py).

## 3. Technical Principles & Constraints
1. **Multi-Threshold Actual + Forecasted Budget Alerts**:
   - Configure tiered alerts on BOTH **actual spend** AND **forecasted month-end spend**:
     - `50%` (Info -> Engineering Slack/Teams channel)
     - `80%` (Warning -> Engineering Lead + Finance Owner)
     - `100%` (Critical / Page -> Immediate root-cause triage & optional non-critical feature throttling)
   - Never rely exclusively on 24–48h delayed cloud billing emails for LLM/API quotas! Pair cloud budgets with **real-time gateway token-spend counters** (`/shadow-ai-eng`, `/shadow-observe`) enforcing per-tenant and per-route daily soft/hard caps!
2. **Real-Time Anomaly Burn-Rate Detection (Hourly, Not Monthly)**:
   - Alert whenever rolling `1h` or `6h` spend exceeds `2.5x` the trailing 14-day same-hour median AND absolute dollar delta exceeds a noise floor (e.g., `>= $25/hr`), eliminating both noisy `$1` false positives and silent `$500/hr` leaks.
3. **Shift-Left CI FinOps Gates (`finops_cost_auditor.py`)**:
   - Run `python shadow-finops/scripts/finops_cost_auditor.py --audit .` in CI on PRs touching Kubernetes YAML, Terraform, or LLM gateway code to catch:
     - Dynamic timestamps inside LLM system prompts (cache-busting!)
     - Unbounded LLM `max_tokens` / `thinking_budget` (`OWASP LLM10:2025`)
     - Missing K8s `resources.requests`/`limits` or unbounded `HPA` `maxReplicas`
     - Missing object-storage lifecycle expiration policies
4. **Ephemeral Preview & Test-Container Zero-Leak Hygiene**:
   - Auto-destroy PR preview stacks on PR close/merge or `48h` TTL; destroy ephemeral local/CI Docker test containers immediately via `--rm --label shadow.ephemeral=true` and `shadow_gate.py --check-docker-leaks`.
5. **Safe Degradation Over Blind Production Outages**:
   - On hard LLM/API budget exhaustion, degrade gracefully (switch non-critical AI summarizers to cached/deterministic fallback or fast cheap model tier) rather than crashing core transactional APIs!

## 4. Architecture & Implementation
### Strict TypeScript Real-Time Anomaly & Tiered Quota Circuit Breaker
```typescript
export type QuotaAction = 'ALLOW' | 'WARN_AND_ALLOW' | 'DOWNGRADE_MODEL_TIER' | 'BLOCK_NON_CRITICAL';

export interface HourlyBurnSnapshot {
  readonly service: string;
  readonly currentHourlyUsd: number;
  readonly trailingMedianHourlyUsd: number;
  readonly monthToDateUsd: number;
  readonly monthlyBudgetUsd: number;
  readonly isCriticalUserFlow: boolean;
}

export function evaluateBurnGuardrail(
  snap: HourlyBurnSnapshot,
): { readonly action: QuotaAction; readonly anomalyDetected: boolean; readonly reason: string } {
  const ratio =
    snap.trailingMedianHourlyUsd > 0
      ? snap.currentHourlyUsd / snap.trailingMedianHourlyUsd
      : 1;
  const absoluteDelta = snap.currentHourlyUsd - snap.trailingMedianHourlyUsd;
  const anomalyDetected = ratio >= 2.5 && absoluteDelta >= 25;

  const pctBudget =
    snap.monthlyBudgetUsd > 0 ? snap.monthToDateUsd / snap.monthlyBudgetUsd : 0;

  if (pctBudget >= 1.0 && !snap.isCriticalUserFlow) {
    return {
      action: 'BLOCK_NON_CRITICAL',
      anomalyDetected,
      reason: 'Monthly budget exhausted (>= 100%); shed non-critical AI/batch flow cleanly.',
    };
  }
  if (pctBudget >= 0.85 || anomalyDetected) {
    return {
      action: 'DOWNGRADE_MODEL_TIER',
      anomalyDetected,
      reason: 'Budget >= 85% or hourly burn spike (>= 2.5x & >= $25/hr); downgrade to efficient model tier and page owner.',
    };
  }
  if (pctBudget >= 0.5) {
    return {
      action: 'WARN_AND_ALLOW',
      anomalyDetected: false,
      reason: '50% monthly budget checkpoint reached.',
    };
  }
  return { action: 'ALLOW', anomalyDetected: false, reason: 'Within normal budget envelope.' };
}
```

### Automated FinOps Audit & Self-Test Commands (`finops_cost_auditor.py`)
```powershell
python "shadow-finops/scripts/finops_cost_auditor.py" --audit .
python "shadow-finops/scripts/finops_cost_auditor.py" --self-test
```

## 5. Platform / Vendor Variations
- **Cloud Provider Native Alerts**: Wire AWS Budgets + AWS Cost Anomaly Detection, GCP Billing Budgets + Pub/Sub webhook, or Azure Cost Alerts into Slack/PagerDuty alongside real-time Prometheus/OTel metrics for LLM token spend (`/shadow-observe`).
- **Multi-Tenant SaaS & Enterprise AI**: Enforce per-tenant token/request quotas in Redis/gateway keyed by `tenant_id` (`tenant_tier`) so a single noisy tenant or prompt-injection loop cannot exhaust the global API key quota for all other customers.

## 6. Decision Matrix & Trade-Offs
| Guardrail Mechanism | Detection Latency | Blast-Radius Protection | Caveat |
| :--- | :--- | :--- | :--- |
| **Provider Monthly Billing Email** | `24–48 hours` (Too slow for LLM loops!) | Low (informational only) | Must supplement with real-time gateway counters |
| **Gateway Real-Time Token Quota + Model Downgrade** | `< 1 second` | **High** — stops runaway spend instantly | Requires clear graceful-degradation UX (`/shadow-design`) |
| **PR CI `finops_cost_auditor.py` Gate** | Pre-merge (`0` prod spend) | Prevents cache-busters & unbounded HPAs shipping | Static scan only; pair with runtime spend alerts |

## 7. Real Production Scenario
**Context:** A newly shipped autonomous document-classifier worker hit a malformed PDF retry loop on Saturday night, calling a frontier reasoning model `18,000` times in 5 hours and burning `$2,700` before anyone checked email on Monday morning.
**Prevention Shipped:** Wiring (1) real-time hourly burn anomaly detection (`>= 2.5x` & `>= $25/hr`), (2) `max_agent_steps = 4` + per-job token circuit breaker, (3) dead-letter quarantine after 3 retries (`/shadow-concurrency`), and (4) `finops_cost_auditor.py --audit .` in CI capped future rogue-loop exposure to `< $30` automatically.

## 8. Failure Modes & Edge Cases
- **WRONG (Relying on month-end cloud invoices to spot runaway LLM loops or hard-killing core checkout APIs when a non-critical budget triggers):** Either discovers `$10k` leaks 3 weeks too late OR causes a self-inflicted `SEV1` outage on revenue traffic.
  **RIGHT:** Detect hourly burn spikes in real time, cap per-route/per-tenant quotas, and shed or downgrade ONLY non-critical AI/batch workloads while keeping core transactional APIs protected.
- **WRONG (Creating noisy anomaly alerts on `$2` percentage spikes with no minimum dollar floor):** Causes alert fatigue until engineers mute the FinOps channel permanently.
  **RIGHT:** Combine relative multiplier (`>= 2.5x`) with an absolute materiality floor (`>= $25/hr`) and route alerts directly to the tagged `team` owner.

## 9. Testing & Verification
- Run `python shadow-finops/scripts/finops_cost_auditor.py --self-test` (`9/9` precision & recall probes) and `python -m unittest discover -s shadow-finops/tests -v`.
- Test budget/anomaly webhook alert routing in Staging with a synthetic threshold before relying on it in Production.

## 10. Operational Considerations
- Hold a concise 30-minute monthly **FinOps Engineering-Finance Sync** reviewing: (1) FOCUS `EffectiveCost` vs `BilledCost` reconciliation, (2) Top 3 Unit Economics trends, (3) `UNATTRIBUTED_SHARED` tag debt %, (4) LLM cache-hit-rate & thinking-token share, and (5) actioned vs open savings tickets.

## 11. Authoritative References
- **FinOps Foundation** — *FinOps Operate Phase: Managing Anomalies, Budgets & FinOps Automation* (`https://www.finops.org/framework/`).
- **OWASP LLM10:2025** — *Unbounded Consumption Mitigation (Rate Limits, Token Caps & Cost Quotas)*.

## 12. Limitations & When NOT to Use
- **Do NOT use** `/shadow-finops` alerts to replace SRE availability/latency SLO burn-rate paging — manage error-budget SLO alerts in `/shadow-observe`.
- **Do NOT auto-terminate** production cloud instances from a budget webhook without explicit `L4` approval and graceful-degradation architecture.
