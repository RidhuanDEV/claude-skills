# 01. Product Metrics & KPI Design

## 1. Purpose & Activation Conditions
Define defensible product metric hierarchies — North Star Metric (NSM), Overall Evaluation Criterion (OEC), input metric trees, and guardrail metrics — that align engineering, product, and executive decisions around real customer value rather than vanity counts. Load when scoping a new product, building a KPI framework, or auditing a dashboard full of conflicting metrics.

## 2. Prerequisites
- Clear statement of the product's core value exchange (what customer outcome creates sustainable retention and revenue).
- Stakeholders from Product, Engineering, and Finance/Operations aligned on data source of truth.

## 3. Technical Principles & Constraints
- **North Star Metric (NSM) Criteria:** A valid NSM MUST satisfy three conditions simultaneously:
  1. Expresses **delivered customer value** (not raw logins, pageviews, or vanity signups),
  2. Acts as a **leading indicator** of long-term revenue/retention,
  3. Is **measurable and influenceable** by product teams within a quarter.
- **Overall Evaluation Criterion (OEC):** For experimentation, translate long-term NSM into a sensitive, short-term, game-resistant OEC (Kohavi, Tang & Xu — *Trustworthy Online Controlled Experiments*). Every experiment specifies **1 Primary OEC**, **2–4 Diagnostic/Secondary Metrics**, and **2–5 Guardrail Metrics**.
- **Guardrail Hierarchy:** Guardrails protect reliability, economics, and user trust (`p95 latency`, `5xx error rate`, `crash-free sessions`, `refund/chargeback rate`, `unsubscribe/churn rate`, `support ticket rate`). A statistically significant degradation on a **blocking guardrail** overrides a positive primary lift.
- **Anti-Goodhart Principle:** Whenever a single metric becomes a target without a counter-metric, teams optimize the proxy at the expense of value (e.g., maximizing `push_click_rate` by clickbaiting notifications until 30-day churn spikes). Pair every growth lever with a quality/retention counter-metric.

## 4. Architecture & Implementation
```typescript
export type MetricRole = 'north_star' | 'oec_primary' | 'input_lever' | 'diagnostic' | 'guardrail_blocking' | 'guardrail_warning';

export interface MetricDefinition {
  readonly id: string;
  readonly name: string;
  readonly role: MetricRole;
  readonly ownerTeam: string;
  readonly grain: 'user' | 'account' | 'session' | 'order';
  readonly numeratorSql: string;
  readonly denominatorSql: string;
  readonly sourceOfTruth: 'warehouse_server' | 'warehouse_client' | 'billing_ledger';
  readonly counterMetricId?: string;
  readonly regressionThresholdPct?: number;
}

export const SAAS_METRIC_TREE: readonly MetricDefinition[] = [
  {
    id: 'nsm_weekly_published_reports',
    name: 'Weekly Active Workspaces Publishing >= 1 Verified Report',
    role: 'north_star',
    ownerTeam: 'product-core',
    grain: 'account',
    numeratorSql: 'COUNT(DISTINCT workspace_id) FILTER (WHERE report_published_count >= 1)',
    denominatorSql: '1',
    sourceOfTruth: 'warehouse_server',
    counterMetricId: 'guardrail_report_error_rate',
  },
  {
    id: 'guardrail_report_error_rate',
    name: 'Report Generation Failure Rate',
    role: 'guardrail_blocking',
    ownerTeam: 'platform-sre',
    grain: 'account',
    numeratorSql: 'COUNT(*) FILTER (WHERE status = \'failed\')',
    denominatorSql: 'COUNT(*)',
    sourceOfTruth: 'warehouse_server',
    regressionThresholdPct: 0.5,
  },
];
```

## 5. Platform / Vendor Variations
| Business Model | Strong NSM Example | Common Vanity Trap | Essential Counter-Metric / Guardrail |
| --- | --- | --- | --- |
| **B2B SaaS** | Weekly active accounts completing core workflow | Total registered accounts | Net revenue retention, p95 workflow latency |
| **E-Commerce / Marketplace** | Repeat buyers completing defect-free orders per 30d | Gross pageviews / Add-to-cart clicks | Refund/return rate, cancellation rate, gross margin |
| **Fintech / Payments** | Successful settled transactions per active merchant | App installs | Fraud/chargeback bps, settlement failure rate |
| **Media / Content** | Weekly readers finishing `>= 3` articles (> 60s read) | Raw clicks / impressions | Bounce rate, subscription churn |

## 6. Decision Matrix & Trade-Offs
| Metric Property | Sensitivity (Speed to Detect) | Long-Term Alignment | Best Role |
| --- | --- | --- | --- |
| **Macro Lagging (90d LTV, Annual Churn)** | Very Low (too slow for 2-week A/B) | Very High | Executive North Star / Quarterly Review |
| **Validated Surrogate OEC (7d Activation + Repeat)** | High | High (if empirically validated) | Primary Experiment OEC |
| **Micro Click-Through (Button CTR)** | Very High | Low (easily gamed) | Diagnostic / Funnel Step Only |

## 7. Real Production Scenario
An e-commerce growth squad sets `Checkout_Button_Clicked` as their quarterly OKR. By making the checkout button oversized and auto-scrolling users to it, clicks jump +28%, yet actual `Order_Completed` stays flat while support complaints about accidental taps rise +19%. Replacing the target with a metric tree anchored on `Completed_NonRefunded_Orders_Per_Visitor` (OEC) + `Checkout_Abandonment` (diagnostic) + `Refund_Rate` & `Checkout_Error_Rate` (blocking guardrails) stops proxy gaming immediately.

## 8. Failure Modes & Edge Cases
- **WRONG:** Tracking 40 unranked KPIs on one executive dashboard with different SQL definitions across teams (`DAU` means "any pageview" in Marketing vs "completed core action" in Product).
- **RIGHT:** Maintain a single version-controlled **Metric Registry** (dbt Semantic Layer / SQL definitions) with one canonical formula, grain, and owner per metric.
- **WRONG:** Using `Average Revenue Per User (ARPU)` in an experiment without checking whale/outlier skewness (one enterprise order swings the entire treatment mean).
- **RIGHT:** Pair raw mean revenue with winsorized/capped revenue (e.g., 99th percentile cap) or conversion rate + conditional AOV, documenting the cap pre-experiment.

## 9. Testing & Verification
- Audit every proposed metric against the **Metric Governance Checklist**: (1) unambiguous numerator/denominator, (2) explicit grain, (3) verified source of truth, (4) assigned owner, (5) paired guardrail/counter-metric.
- Validate surrogate OECs historically: confirm changes in the short-term proxy actually correlate with 60–90 day retention or LTV before using it for ship decisions.

## 10. Operational Considerations
- Review the metric tree semi-annually as product stage shifts (Pre-PMF focuses on Activation & Retention; Growth stage balances Acquisition Efficiency & Monetization).
- Version metric definitions (`metric_v1 -> metric_v2`) and run a 14-day shadow comparison before deprecating an executive KPI so historical trendlines never silently shift.

## 11. Authoritative References
- Ron Kohavi, Diane Tang & Ya Xu — *Trustworthy Online Controlled Experiments: A Practical Guide to A/B Testing* (Cambridge University Press, Ch. 7: Metrics for Experimentation & OEC).
- Amplitude — *North Star Playbook* (`https://amplitude.com/books/north-star`).
- dbt Labs — *Semantic Layer & Metric Governance* (`https://docs.getdbt.com/docs/use-dbt-semantic-layer/dbt-sl`).

## 12. Limitations & When NOT to Use
- Do NOT invent an elaborate multi-tier metric tree for a 2-week internal prototype or pre-launch MVP with `< 50` users; qualitative user interviews and simple activation tracking yield faster truth.
- Never replace qualitative UX research with quantitative metrics alone — metrics tell you *where* users drop off, rarely *why*.
