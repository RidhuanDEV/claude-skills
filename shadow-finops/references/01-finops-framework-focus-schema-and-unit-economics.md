# 01. FinOps Foundation Framework, FOCUS Billing Normalization & Unit Economics

## 1. Purpose & Activation Conditions
Use this playbook in the **Inform** phase of the FinOps lifecycle (`Inform -> Optimize -> Operate`) to normalize multi-cloud, Kubernetes, database, and AI/LLM provider invoices into the vendor-neutral **FOCUS (FinOps Open Cost and Usage Specification)** schema, reconcile unattributed shared spend transparently, and compute decision-grade **Unit Economics** (e.g., cost per 1,000 API calls, cost per resolved support ticket, cost per active tenant/month).

Activate this playbook when:
- Reconciling cloud or SaaS billing exports (`AWS CUR`, `GCP BigQuery Billing`, `Azure Cost Management`, OpenAI/Anthropic/Vertex usage exports) across accounts and teams.
- Designing cost allocation tags (`service`, `env`, `team`, `feature`, and privacy-safe `tenant_tier` when supported) without silently inventing unmeasured tenant allocations.
- Building executive showback/chargeback dashboards separating amortized `EffectiveCost` from cash-basis `BilledCost`.

## 2. Prerequisites
- Billing export schema / contract dimensions actually present in the organization's cloud/AI accounts (`test_finops_reconciliation.py`).
- Privacy boundary check with `/shadow-privacy` before introducing tenant-level tags so billing exports never leak PII (`email`, `NIK`, personal customer names).

## 3. Technical Principles & Constraints
1. **FinOps Foundation 3 Phases & 4 Core Domains**:
   - **Phases**: `Inform` (visibility, allocation, unit economics) -> `Optimize` (usage + rate + architectural efficiency) -> `Operate` (budgets, anomaly response, CI/CD guardrails).
   - **4 Domains**: *(1) Understand Usage & Cost*, *(2) Quantify Business Value*, *(3) Optimize Usage & Cost*, *(4) Manage the FinOps Practice*.
2. **FOCUS Canonical Columns (Never Lock BI Queries to Vendor-Proprietary Column Names)**:
   - **`EffectiveCost`**: Amortized cost incorporating Savings Plans, Committed Use Discounts (`CUD`), upfront fees, and negotiated discounts — **ALWAYS use `EffectiveCost` for unit economics and engineering optimization decisions!**
   - **`BilledCost`**: Cash-basis invoice outflow after credits/discounts — **use `BilledCost` for Finance AP cash reconciliation** (prepaid annual commitment spikes appear on Month 1 invoice in `BilledCost`, distorting engineering trends if misused!).
   - **`ListCost` vs `ContractedCost`**: Benchmarks negotiated rate discounts (`Effective Savings Rate — ESR`).
   - **`ChargeCategory`**: `Usage | Purchase | Tax | Credit | Adjustment`; **`PricingCategory`**: `On-Demand | Commitment | Dynamic`.
   - Core grouping keys: `ServiceCategory`, `ServiceName`, `SubAccountId`, `RegionId`, `ResourceId`, `Tags`.
3. **Honest Reconciliation of Unattributed Shared Spend (`test_finops_reconciliation.py`)**:
   - Allocate costs strictly using **allocation dimensions actually present in the billing contract**.
   - Reconcile shared/untagged infrastructure (NAT gateways, shared clusters, control planes, untagged legacy volumes) in an explicit **`UNATTRIBUTED_SHARED`** bucket so `sum(allocated_buckets) + unattributed_shared === total_invoice_cost` (`0` silent rounding or fabricated splits!).
   - Include `tenant_tier` ONLY when both the cost model AND privacy boundaries support it.
4. **Unit Economics Over Raw Total Spend**:
   - Raw cloud spend rising `+25%` while revenue-generating requests grow `+80%` is a *healthy* scale win (`unit cost -31%`). Raw cloud spend rising `+25%` while active usage stays flat is a severe cost regression! Always pair total `EffectiveCost` with primary business driver metrics.

## 4. Architecture & Implementation
### Strict TypeScript FOCUS Reconciliation & Unit Economics Calculator
```typescript
export interface FocusCostRow {
  readonly serviceName: string;
  readonly chargeCategory: 'Usage' | 'Purchase' | 'Tax' | 'Credit' | 'Adjustment';
  readonly effectiveCostUsd: number;
  readonly billedCostUsd: number;
  readonly teamTag: string | null;
}

export interface ReconciledSpendSummary {
  readonly totalEffectiveCostUsd: number;
  readonly totalBilledCostUsd: number;
  readonly byTeamEffectiveUsd: Readonly<Record<string, number>>;
  readonly unattributedSharedUsd: number;
  readonly effectiveCostPerThousandUnitsUsd: number | null;
}

export function reconcileFocusSpend(
  rows: readonly FocusCostRow[],
  completedBusinessUnits: number,
): ReconciledSpendSummary {
  let totalEffective = 0;
  let totalBilled = 0;
  let unattributedShared = 0;
  const byTeam: Record<string, number> = {};

  for (const row of rows) {
    totalEffective += row.effectiveCostUsd;
    totalBilled += row.billedCostUsd;
    if (row.chargeCategory !== 'Usage') {
      unattributedShared += row.effectiveCostUsd;
      continue;
    }
    const team = row.teamTag?.trim();
    if (!team) {
      unattributedShared += row.effectiveCostUsd;
    } else {
      byTeam[team] = (byTeam[team] ?? 0) + row.effectiveCostUsd;
    }
  }

  const unitCost =
    completedBusinessUnits > 0
      ? (totalEffective / completedBusinessUnits) * 1000
      : null;

  return {
    totalEffectiveCostUsd: Number(totalEffective.toFixed(4)),
    totalBilledCostUsd: Number(totalBilled.toFixed(4)),
    byTeamEffectiveUsd: byTeam,
    unattributedSharedUsd: Number(unattributedShared.toFixed(4)),
    effectiveCostPerThousandUnitsUsd:
      unitCost !== null ? Number(unitCost.toFixed(4)) : null,
  };
}
```

### Standard FOCUS Allocation SQL Pattern (Amortized Engineering View)
```sql
SELECT
  COALESCE(NULLIF(Tags['team'], ''), 'UNATTRIBUTED_SHARED') AS cost_owner,
  ServiceCategory,
  PricingCategory,
  ROUND(SUM(EffectiveCost), 2) AS effective_cost_usd,
  ROUND(SUM(BilledCost), 2) AS billed_cost_usd
FROM focus_billing_export
WHERE ChargePeriodStart >= DATE '2026-04-01'
  AND ChargePeriodEnd < DATE '2026-05-01'
GROUP BY 1, 2, 3
ORDER BY effective_cost_usd DESC;
```

## 5. Platform / Vendor Variations
- **AWS / GCP / Azure Native FOCUS Exports**: Enable native FOCUS 1.0+ billing exports directly (AWS Data Exports FOCUS, GCP Billing Export FOCUS view, Azure Cost Management FOCUS export) rather than hand-maintaining fragile legacy CSV mappers.
- **AI / LLM & Third-Party SaaS (OpenAI / Anthropic / Gemini / Datadog / Snowflake)**: Map API usage CSVs into the same FOCUS schema (`ServiceCategory = 'AI and Machine Learning'`, `ChargeCategory = 'Usage'`, `Tags = {service, feature, env}`) so LLM token spend sits alongside compute and database costs in one unified unit-economics view.

## 6. Decision Matrix & Trade-Offs
| Metric Choice | Use Case | Pitfall if Misused |
| :--- | :--- | :--- |
| **`EffectiveCost`** | Engineering showback, unit economics, monthly trend comparison | Doesn't match Month-1 cash outflow on upfront Reserved/CUD purchases |
| **`BilledCost`** | Accounting / AP invoice reconciliation | Spikes artificially in upfront-purchase months and hides amortized daily burn |
| **`UNATTRIBUTED_SHARED` Bucket** | Explicit reconciliation of untagged/shared spend | Hiding untagged spend or arbitrarily forcing fake splits obscures tagging debt |

## 7. Real Production Scenario
**Context:** Finance alarmed engineering that AWS spend jumped `+$42,000` in January (`BilledCost`), demanding an emergency freeze on Kubernetes autoscaling.
**FinOps Clarification:** Normalizing the export to **FOCUS** revealed `$38,500` was a 1-year upfront RDS Reserved Instance purchase (`ChargeCategory = 'Purchase'`), while actual amortized **`EffectiveCost`** fell `-14%` and `EffectiveCost / 1,000 API calls` dropped from `$0.42` to `$0.33`! Distinguishing `EffectiveCost` from `BilledCost` averted an unnecessary infrastructure freeze and exposed `$4,100/mo` sitting in `UNATTRIBUTED_SHARED` orphaned snapshots ready for cleanup.

## 8. Failure Modes & Edge Cases
- **WRONG (Mixing `BilledCost` into unit-economics curves or silently dropping untagged shared spend so team totals don't reconcile to the invoice):** Destroys Finance-Engineering trust during monthly FinOps reviews.
  **RIGHT:** Use `EffectiveCost` for unit economics, `BilledCost` for invoice cash reconciliation, and reconcile 100% of untagged/shared spend explicitly in `UNATTRIBUTED_SHARED`.
- **WRONG (Putting raw customer emails or `NIK` into cloud resource `Tags` for per-tenant billing):** Leaks Specific PII into billing exports accessible to finance/BI tools (`/shadow-privacy`).
  **RIGHT:** Tag strictly with opaque `tenant_tier` or anonymized hash IDs when supported by privacy policy.

## 9. Testing & Verification
- Run `python -m unittest discover -s shadow-finops/tests -v` (`test_finops_reconciliation.py` validates reconciliation of allocated vs unattributed shared spend).
- Verify `sum(by_team) + unattributed_shared === total_effective_cost` within floating-point tolerance (`<= $0.01`) on every generated showback report.

## 10. Operational Considerations
- Track **Tag Compliance Rate (`% of EffectiveCost attributed to valid service + team + env`)** monthly targeting `>= 90%`, enforcing mandatory tags via IaC CI checks (`/shadow-ops`).

## 11. Authoritative References
- **FinOps Foundation Framework** — `https://www.finops.org/framework/` (*Inform, Optimize, Operate* & 4 Core Domains).
- **FOCUS Specification (FinOps Open Cost and Usage Specification)** — `https://focus.finops.org/`.

## 12. Limitations & When NOT to Use
- **Do NOT use** `/shadow-finops` for pre-award government RFP/KAK commercial BoQ pricing under Perpres 46/2025 — route pre-sales commercial bids to `/shadow-presales`.
- **Do NOT audit** Kubernetes clusters unnecessarily when the Monarch strictly asks for a standalone LLM token-cost estimate (`02-ai-llm-token-economics-prefix-caching-and-thinking-caps.md`).
